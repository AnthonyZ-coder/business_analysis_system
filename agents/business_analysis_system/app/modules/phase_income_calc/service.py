import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import DB_PATH
from app.modules.phase_income_calc.schemas import (
    PhaseIncomeCreateRequest,
    PhaseIncomeUpdateRequest,
)


class PhaseIncomeCalcService:
    """
    phase_income_calc module service

    Current MVP responsibilities:
    - search contracts / projects
    - list available split rules
    - create phase income record and calculate amounts
    - query phase income record
    - update phase income record and recalculate
    - build downstream payload
    """

    def __init__(self) -> None:
        self.db_path = str(DB_PATH)

    # ============================================================
    # Search / Query
    # ============================================================
    def search_contracts(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        keyword = (keyword or "").strip()
        if not keyword:
            return []

        with self._get_conn() as conn:
            cursor = conn.cursor()
            like_keyword = f"%{keyword}%"

            cursor.execute(
                """
                SELECT
                    c.id AS contract_id,
                    c.contract_code,
                    c.contract_name,
                    c.project_code,
                    p.project_name,
                    c.customer_name
                FROM contract_info c
                LEFT JOIN project_info p ON c.project_code = p.project_code
                WHERE
                    c.contract_name LIKE ?
                    OR c.contract_code LIKE ?
                    OR c.project_code LIKE ?
                    OR p.project_name LIKE ?
                ORDER BY c.id DESC
                LIMIT ?
                """,
                (
                    like_keyword,
                    like_keyword,
                    like_keyword,
                    like_keyword,
                    limit,
                ),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "contract_id": row["contract_id"],
                        "contract_code": row["contract_code"],
                        "contract_name": row["contract_name"],
                        "project_code": row["project_code"],
                        "project_name": row["project_name"],
                        "customer_name": row["customer_name"],
                    }
                )
            return results

    def list_rules(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id, rule_code, rule_name, rule_type, project_type_tag,
                    applicable_scope, category_split_json, status
                FROM product_split_rule
                WHERE status = 'ENABLED'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "rule_id": row["id"],
                        "rule_code": row["rule_code"],
                        "rule_name": row["rule_name"],
                        "rule_type": row["rule_type"],
                        "project_type_tag": row["project_type_tag"],
                        "applicable_scope": row["applicable_scope"],
                        "category_split_json": self._load_json(row["category_split_json"]),
                        "status": row["status"],
                    }
                )
            return results

    # ============================================================
    # Create / Update / Get
    # ============================================================
    def create_phase_income_record(self, request: PhaseIncomeCreateRequest) -> Dict[str, Any]:
        self._validate_project_code_exists(request.project_code)
        self._validate_rule_exists(request.rule_id)

        contract_info = self._resolve_contract_info(
            contract_id=request.contract_id,
            contract_code=request.contract_code,
            contract_name=request.contract_name,
        )

        project_name = request.project_name or self._get_project_name(request.project_code)
        rule_info = self._get_rule_basic_info(request.rule_id)
        rule_details = self._get_rule_details(request.rule_id)

        if not rule_details:
            raise HTTPException(status_code=400, detail="selected rule has no detail items")

        amount_result = self._calculate_tax_amounts(
            input_amount=request.input_amount,
            amount_type=request.amount_type,
            tax_rate=request.tax_rate,
        )

        detail_results = self._calculate_phase_income_details(
            rule_details=rule_details,
            tax_included_amount=amount_result["tax_included_amount"],
            tax_excluded_amount=amount_result["tax_excluded_amount"],
        )
        category_summary = self._build_category_summary(detail_results)

        phase_income_code = self._generate_code("PIC")

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO phase_income_record
                (
                    phase_income_code, billing_period, billing_date,
                    project_code, project_name,
                    contract_id, contract_code, contract_name,
                    rule_id, rule_code, rule_name,
                    input_amount, amount_type,
                    tax_included_amount, tax_excluded_amount, tax_rate,
                    calc_status, source_type,
                    created_by, updated_by, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    phase_income_code,
                    request.billing_period,
                    request.billing_date.isoformat() if request.billing_date else None,
                    request.project_code,
                    project_name,
                    contract_info["contract_id"],
                    contract_info["contract_code"],
                    contract_info["contract_name"],
                    request.rule_id,
                    rule_info["rule_code"],
                    rule_info["rule_name"],
                    str(self._quantize_money(request.input_amount)),
                    request.amount_type,
                    str(amount_result["tax_included_amount"]),
                    str(amount_result["tax_excluded_amount"]),
                    str(request.tax_rate),
                    "CALCULATED",
                    request.source_type,
                    request.created_by,
                    request.created_by,
                    request.remarks,
                ),
            )
            phase_income_id = cursor.lastrowid

            detail_rows = []
            for index, item in enumerate(detail_results, start=1):
                detail_rows.append(
                    (
                        phase_income_id,
                        item["product_code"],
                        item["product_name"],
                        item["category_code"],
                        str(item["split_ratio"]),
                        str(item["tax_included_amount"]),
                        str(item["tax_excluded_amount"]),
                        index,
                        None,
                    )
                )

            cursor.executemany(
                """
                INSERT INTO phase_income_detail
                (
                    phase_income_id, product_code, product_name, category_code,
                    split_ratio, tax_included_amount, tax_excluded_amount,
                    sort_order, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                detail_rows,
            )

            summary_rows = []
            for item in category_summary:
                summary_rows.append(
                    (
                        phase_income_id,
                        item["category_code"],
                        item["category_name"],
                        str(item["split_ratio"]),
                        str(item["tax_included_amount"]),
                        str(item["tax_excluded_amount"]),
                        None,
                    )
                )

            cursor.executemany(
                """
                INSERT INTO phase_income_category_summary
                (
                    phase_income_id, category_code, category_name,
                    split_ratio, tax_included_amount, tax_excluded_amount, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                summary_rows,
            )

            conn.commit()

        return self.get_phase_income_record(phase_income_id)

    def get_phase_income_record(self, record_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, phase_income_code, billing_period, billing_date,
                    project_code, project_name,
                    contract_id, contract_code, contract_name,
                    rule_id, rule_code, rule_name,
                    input_amount, amount_type,
                    tax_included_amount, tax_excluded_amount, tax_rate,
                    calc_status, source_type,
                    created_at, updated_at, created_by, updated_by, remarks
                FROM phase_income_record
                WHERE id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="phase income record not found")

            details = self._get_phase_income_details(record_id, conn)
            category_summary = self._get_phase_income_category_summary(record_id, conn)

            return {
                "id": row["id"],
                "phase_income_code": row["phase_income_code"],
                "billing_period": row["billing_period"],
                "billing_date": self._parse_date(row["billing_date"]),
                "project_code": row["project_code"],
                "project_name": row["project_name"],
                "contract_id": row["contract_id"],
                "contract_code": row["contract_code"],
                "contract_name": row["contract_name"],
                "rule_id": row["rule_id"],
                "rule_code": row["rule_code"],
                "rule_name": row["rule_name"],
                "input_amount": self._to_decimal_required(row["input_amount"]),
                "amount_type": row["amount_type"],
                "tax_included_amount": self._to_decimal_required(row["tax_included_amount"]),
                "tax_excluded_amount": self._to_decimal_required(row["tax_excluded_amount"]),
                "tax_rate": self._to_decimal_required(row["tax_rate"]),
                "calc_status": row["calc_status"],
                "source_type": row["source_type"],
                "created_at": self._parse_datetime(row["created_at"]),
                "updated_at": self._parse_datetime(row["updated_at"]),
                "created_by": row["created_by"],
                "updated_by": row["updated_by"],
                "remarks": row["remarks"],
                "details": details,
                "category_summary": category_summary,
            }

    def update_phase_income_record(self, record_id: int, request: PhaseIncomeUpdateRequest) -> Dict[str, Any]:
        current = self.get_phase_income_record(record_id)

        billing_period = request.billing_period or current["billing_period"]
        billing_date = request.billing_date if request.billing_date is not None else current["billing_date"]

        project_code = current["project_code"]
        project_name = request.project_name if request.project_name is not None else current["project_name"]

        contract_id = request.contract_id if request.contract_id is not None else current["contract_id"]
        contract_code = request.contract_code if request.contract_code is not None else current["contract_code"]
        contract_name = request.contract_name if request.contract_name is not None else current["contract_name"]

        rule_id = request.rule_id if request.rule_id is not None else current["rule_id"]
        self._validate_rule_exists(rule_id)

        rule_info = self._get_rule_basic_info(rule_id)
        rule_details = self._get_rule_details(rule_id)
        if not rule_details:
            raise HTTPException(status_code=400, detail="selected rule has no detail items")

        input_amount = request.input_amount if request.input_amount is not None else current["input_amount"]
        amount_type = request.amount_type if request.amount_type is not None else current["amount_type"]
        tax_rate = request.tax_rate if request.tax_rate is not None else current["tax_rate"]
        calc_status = request.calc_status if request.calc_status is not None else current["calc_status"]

        amount_result = self._calculate_tax_amounts(
            input_amount=input_amount,
            amount_type=amount_type,
            tax_rate=tax_rate,
        )

        detail_results = self._calculate_phase_income_details(
            rule_details=rule_details,
            tax_included_amount=amount_result["tax_included_amount"],
            tax_excluded_amount=amount_result["tax_excluded_amount"],
        )
        category_summary = self._build_category_summary(detail_results)

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE phase_income_record
                SET
                    billing_period = ?,
                    billing_date = ?,
                    project_name = ?,
                    contract_id = ?,
                    contract_code = ?,
                    contract_name = ?,
                    rule_id = ?,
                    rule_code = ?,
                    rule_name = ?,
                    input_amount = ?,
                    amount_type = ?,
                    tax_included_amount = ?,
                    tax_excluded_amount = ?,
                    tax_rate = ?,
                    calc_status = ?,
                    updated_by = ?,
                    remarks = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    billing_period,
                    billing_date.isoformat() if isinstance(billing_date, date) else billing_date,
                    project_name,
                    contract_id,
                    contract_code,
                    contract_name,
                    rule_id,
                    rule_info["rule_code"],
                    rule_info["rule_name"],
                    str(self._quantize_money(input_amount)),
                    amount_type,
                    str(amount_result["tax_included_amount"]),
                    str(amount_result["tax_excluded_amount"]),
                    str(tax_rate),
                    calc_status,
                    request.updated_by,
                    request.remarks if request.remarks is not None else current["remarks"],
                    record_id,
                ),
            )

            cursor.execute("DELETE FROM phase_income_detail WHERE phase_income_id = ?", (record_id,))
            cursor.execute("DELETE FROM phase_income_category_summary WHERE phase_income_id = ?", (record_id,))

            detail_rows = []
            for index, item in enumerate(detail_results, start=1):
                detail_rows.append(
                    (
                        record_id,
                        item["product_code"],
                        item["product_name"],
                        item["category_code"],
                        str(item["split_ratio"]),
                        str(item["tax_included_amount"]),
                        str(item["tax_excluded_amount"]),
                        index,
                        None,
                    )
                )
            cursor.executemany(
                """
                INSERT INTO phase_income_detail
                (
                    phase_income_id, product_code, product_name, category_code,
                    split_ratio, tax_included_amount, tax_excluded_amount,
                    sort_order, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                detail_rows,
            )

            summary_rows = []
            for item in category_summary:
                summary_rows.append(
                    (
                        record_id,
                        item["category_code"],
                        item["category_name"],
                        str(item["split_ratio"]),
                        str(item["tax_included_amount"]),
                        str(item["tax_excluded_amount"]),
                        None,
                    )
                )
            cursor.executemany(
                """
                INSERT INTO phase_income_category_summary
                (
                    phase_income_id, category_code, category_name,
                    split_ratio, tax_included_amount, tax_excluded_amount, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                summary_rows,
            )

            conn.commit()

        return self.get_phase_income_record(record_id)

    # ============================================================
    # Internal Payload
    # ============================================================
    def build_phase_income_internal_payload(self, record_id: int) -> Dict[str, Any]:
        record = self.get_phase_income_record(record_id)

        return {
            "record_type": "phase_income_record",
            "record_id": record["id"],
            "business_key": record["phase_income_code"],
            "status": record["calc_status"],
            "next_step": "RESULT_STORAGE",
            "payload": {
                "phase_income_code": record["phase_income_code"],
                "billing_period": record["billing_period"],
                "project_code": record["project_code"],
                "project_name": record["project_name"],
                "contract_id": record["contract_id"],
                "contract_code": record["contract_code"],
                "contract_name": record["contract_name"],
                "rule_id": record["rule_id"],
                "rule_code": record["rule_code"],
                "rule_name": record["rule_name"],
                "input_amount": str(record["input_amount"]),
                "amount_type": record["amount_type"],
                "tax_included_amount": str(record["tax_included_amount"]),
                "tax_excluded_amount": str(record["tax_excluded_amount"]),
                "tax_rate": str(record["tax_rate"]),
                "details": [
                    {
                        "product_code": item["product_code"],
                        "product_name": item["product_name"],
                        "category_code": item["category_code"],
                        "split_ratio": str(item["split_ratio"]),
                        "tax_included_amount": str(item["tax_included_amount"]),
                        "tax_excluded_amount": str(item["tax_excluded_amount"]),
                    }
                    for item in record["details"]
                ],
                "category_summary": [
                    {
                        "category_code": item["category_code"],
                        "category_name": item["category_name"],
                        "split_ratio": str(item["split_ratio"]),
                        "tax_included_amount": str(item["tax_included_amount"]),
                        "tax_excluded_amount": str(item["tax_excluded_amount"]),
                    }
                    for item in record["category_summary"]
                ],
            },
            "warnings": [],
            "trace": {
                "module": "phase_income_calc",
                "reserved_for": ["result_storage"],
            },
        }

    # ============================================================
    # Calculation Helpers
    # ============================================================
    def _calculate_tax_amounts(
        self,
        input_amount: Decimal,
        amount_type: str,
        tax_rate: Decimal,
    ) -> Dict[str, Decimal]:
        input_amount = self._quantize_money(input_amount)
        tax_rate = self._to_decimal_required(tax_rate)

        divisor = Decimal("1") + tax_rate
        if divisor <= Decimal("0"):
            raise HTTPException(status_code=400, detail="invalid tax_rate")

        if amount_type == "TAX_INCLUDED":
            tax_included_amount = input_amount
            tax_excluded_amount = self._quantize_money(input_amount / divisor)
        elif amount_type == "TAX_EXCLUDED":
            tax_excluded_amount = input_amount
            tax_included_amount = self._quantize_money(input_amount * divisor)
        else:
            raise HTTPException(status_code=400, detail="amount_type must be TAX_INCLUDED or TAX_EXCLUDED")

        return {
            "tax_included_amount": tax_included_amount,
            "tax_excluded_amount": tax_excluded_amount,
        }

    def _calculate_phase_income_details(
        self,
        rule_details: List[Dict[str, Any]],
        tax_included_amount: Decimal,
        tax_excluded_amount: Decimal,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for item in rule_details:
            split_ratio = self._to_decimal_required(item["split_ratio"])
            detail_tax_included_amount = self._quantize_money(tax_included_amount * split_ratio)
            detail_tax_excluded_amount = self._quantize_money(tax_excluded_amount * split_ratio)

            results.append(
                {
                    "product_code": item["product_code"],
                    "product_name": item["product_name"],
                    "category_code": item["category_code"],
                    "split_ratio": split_ratio,
                    "tax_included_amount": detail_tax_included_amount,
                    "tax_excluded_amount": detail_tax_excluded_amount,
                }
            )

        return results

    def _build_category_summary(self, detail_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        category_map: Dict[str, Dict[str, Any]] = {}

        for item in detail_results:
            category_code = item["category_code"]
            if category_code not in category_map:
                category_map[category_code] = {
                    "category_code": category_code,
                    "category_name": self._get_category_name(category_code),
                    "split_ratio": Decimal("0"),
                    "tax_included_amount": Decimal("0"),
                    "tax_excluded_amount": Decimal("0"),
                }

            category_map[category_code]["split_ratio"] += item["split_ratio"]
            category_map[category_code]["tax_included_amount"] += item["tax_included_amount"]
            category_map[category_code]["tax_excluded_amount"] += item["tax_excluded_amount"]

        results: List[Dict[str, Any]] = []
        for category_code, value in category_map.items():
            results.append(
                {
                    "category_code": category_code,
                    "category_name": value["category_name"],
                    "split_ratio": self._quantize_ratio(value["split_ratio"]),
                    "tax_included_amount": self._quantize_money(value["tax_included_amount"]),
                    "tax_excluded_amount": self._quantize_money(value["tax_excluded_amount"]),
                }
            )

        results.sort(key=lambda x: x["category_code"])
        return results

    # ============================================================
    # DB Query Helpers
    # ============================================================
    def _get_phase_income_details(self, record_id: int, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, phase_income_id, product_code, product_name, category_code,
                split_ratio, tax_included_amount, tax_excluded_amount,
                sort_order, created_at, updated_at, remarks
            FROM phase_income_detail
            WHERE phase_income_id = ?
            ORDER BY sort_order, id
            """,
            (record_id,),
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "phase_income_id": row["phase_income_id"],
                    "product_code": row["product_code"],
                    "product_name": row["product_name"],
                    "category_code": row["category_code"],
                    "split_ratio": self._to_decimal_required(row["split_ratio"]),
                    "tax_included_amount": self._to_decimal_required(row["tax_included_amount"]),
                    "tax_excluded_amount": self._to_decimal_required(row["tax_excluded_amount"]),
                    "sort_order": row["sort_order"],
                    "created_at": self._parse_datetime(row["created_at"]),
                    "updated_at": self._parse_datetime(row["updated_at"]),
                    "remarks": row["remarks"],
                }
            )
        return results

    def _get_phase_income_category_summary(self, record_id: int, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, phase_income_id, category_code, category_name,
                split_ratio, tax_included_amount, tax_excluded_amount,
                created_at, updated_at, remarks
            FROM phase_income_category_summary
            WHERE phase_income_id = ?
            ORDER BY category_code, id
            """,
            (record_id,),
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "phase_income_id": row["phase_income_id"],
                    "category_code": row["category_code"],
                    "category_name": row["category_name"],
                    "split_ratio": self._to_decimal_required(row["split_ratio"]),
                    "tax_included_amount": self._to_decimal_required(row["tax_included_amount"]),
                    "tax_excluded_amount": self._to_decimal_required(row["tax_excluded_amount"]),
                    "created_at": self._parse_datetime(row["created_at"]),
                    "updated_at": self._parse_datetime(row["updated_at"]),
                    "remarks": row["remarks"],
                }
            )
        return results

    def _resolve_contract_info(
        self,
        contract_id: Optional[int],
        contract_code: Optional[str],
        contract_name: Optional[str],
    ) -> Dict[str, Optional[Any]]:
        if contract_id is None and not contract_code and not contract_name:
            return {
                "contract_id": None,
                "contract_code": None,
                "contract_name": None,
            }

        with self._get_conn() as conn:
            cursor = conn.cursor()

            if contract_id is not None:
                cursor.execute(
                    """
                    SELECT id, contract_code, contract_name
                    FROM contract_info
                    WHERE id = ?
                    """,
                    (contract_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail="contract_id does not exist")
                return {
                    "contract_id": row["id"],
                    "contract_code": row["contract_code"],
                    "contract_name": row["contract_name"],
                }

            if contract_code:
                cursor.execute(
                    """
                    SELECT id, contract_code, contract_name
                    FROM contract_info
                    WHERE contract_code = ?
                    """,
                    (contract_code,),
                )
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail="contract_code does not exist")
                return {
                    "contract_id": row["id"],
                    "contract_code": row["contract_code"],
                    "contract_name": row["contract_name"],
                }

            if contract_name:
                cursor.execute(
                    """
                    SELECT id, contract_code, contract_name
                    FROM contract_info
                    WHERE contract_name = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (contract_name,),
                )
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail="contract_name does not exist")
                return {
                    "contract_id": row["id"],
                    "contract_code": row["contract_code"],
                    "contract_name": row["contract_name"],
                }

        raise HTTPException(status_code=400, detail="failed to resolve contract info")

    def _get_rule_basic_info(self, rule_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, rule_code, rule_name, status
                FROM product_split_rule
                WHERE id = ?
                """,
                (rule_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="rule_id does not exist")
            if row["status"] != "ENABLED":
                raise HTTPException(status_code=400, detail="rule is not enabled")

            return {
                "rule_id": row["id"],
                "rule_code": row["rule_code"],
                "rule_name": row["rule_name"],
                "status": row["status"],
            }

    def _get_rule_details(self, rule_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id, rule_id, product_code, product_name, category_code,
                    split_ratio, source_type, based_draft_detail_id,
                    sort_order, created_at, updated_at, remarks
                FROM product_split_rule_detail
                WHERE rule_id = ?
                ORDER BY sort_order, id
                """,
                (rule_id,),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "id": row["id"],
                        "rule_id": row["rule_id"],
                        "product_code": row["product_code"],
                        "product_name": row["product_name"],
                        "category_code": row["category_code"],
                        "split_ratio": self._to_decimal_required(row["split_ratio"]),
                        "source_type": row["source_type"],
                        "based_draft_detail_id": row["based_draft_detail_id"],
                        "sort_order": row["sort_order"],
                        "created_at": self._parse_datetime(row["created_at"]),
                        "updated_at": self._parse_datetime(row["updated_at"]),
                        "remarks": row["remarks"],
                    }
                )
            return results

    # ============================================================
    # Validation Helpers
    # ============================================================
    def _validate_project_code_exists(self, project_code: str) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM project_info WHERE project_code = ?", (project_code,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="project_code does not exist")

    def _validate_rule_exists(self, rule_id: int) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM product_split_rule WHERE id = ?", (rule_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="rule_id does not exist")

    def _get_project_name(self, project_code: str) -> Optional[str]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT project_name FROM project_info WHERE project_code = ?",
                (project_code,),
            )
            row = cursor.fetchone()
            return row["project_name"] if row else None

    def _get_category_name(self, category_code: str) -> str:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT category_name
                FROM product_line_category
                WHERE category_code = ?
                """,
                (category_code,),
            )
            row = cursor.fetchone()
            return row["category_name"] if row else category_code

    # ============================================================
    # Basic Helpers
    # ============================================================
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _generate_code(self, prefix: str) -> str:
        return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8].upper()}"

    def _dump_json(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def _load_json(self, value: Optional[str]) -> Optional[Any]:
        if not value:
            return None
        try:
            return json.loads(value)
        except Exception:
            return None

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return None

    def _parse_date(self, value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except Exception:
            return None

    def _to_decimal_required(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"invalid decimal value: {value}")

    def _quantize_money(self, value: Decimal) -> Decimal:
        value = self._to_decimal_required(value)
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _quantize_ratio(self, value: Decimal) -> Decimal:
        value = self._to_decimal_required(value)
        return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)