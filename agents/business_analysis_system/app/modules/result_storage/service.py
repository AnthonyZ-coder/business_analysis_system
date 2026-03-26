import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import DB_PATH
from app.modules.result_storage.schemas import (
    ResultStorageCreateFromPhaseIncomeRequest,
    WorkflowStatusLogCreateRequest,
)


class ResultStorageService:
    """
    result_storage module service

    Current MVP responsibilities:
    - create result record from phase_income_record
    - query result record
    - create workflow status log
    - query workflow status logs
    - build downstream payload
    """

    def __init__(self) -> None:
        self.db_path = str(DB_PATH)

    # ============================================================
    # Result Storage
    # ============================================================
    def create_result_from_phase_income(
        self,
        phase_income_record_id: int,
        request: ResultStorageCreateFromPhaseIncomeRequest,
    ) -> Dict[str, Any]:
        phase_income_record = self._get_phase_income_record(phase_income_record_id)

        existing_result = self._find_existing_result_by_source(
            source_record_type="phase_income_record",
            source_record_id=phase_income_record_id,
        )
        if existing_result:
            raise HTTPException(
                status_code=400,
                detail="result storage record already exists for this phase income record",
            )

        phase_income_details = self._get_phase_income_details(phase_income_record_id)
        if not phase_income_details:
            raise HTTPException(
                status_code=400,
                detail="phase income detail is empty, cannot store result",
            )

        result_code = self._generate_code("RST")

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO result_storage_record
                (
                    result_code, source_record_type, source_record_id,
                    billing_period, billing_date,
                    project_code, project_name,
                    contract_id, contract_code, contract_name,
                    rule_id, rule_code, rule_name,
                    input_amount, amount_type,
                    tax_included_amount, tax_excluded_amount, tax_rate,
                    result_status, version_no,
                    created_by, updated_by, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_code,
                    "phase_income_record",
                    phase_income_record["id"],
                    phase_income_record["billing_period"],
                    phase_income_record["billing_date"].isoformat() if phase_income_record["billing_date"] else None,
                    phase_income_record["project_code"],
                    phase_income_record["project_name"],
                    phase_income_record["contract_id"],
                    phase_income_record["contract_code"],
                    phase_income_record["contract_name"],
                    phase_income_record["rule_id"],
                    phase_income_record["rule_code"],
                    phase_income_record["rule_name"],
                    str(phase_income_record["input_amount"]),
                    phase_income_record["amount_type"],
                    str(phase_income_record["tax_included_amount"]),
                    str(phase_income_record["tax_excluded_amount"]),
                    str(phase_income_record["tax_rate"]),
                    "STORED",
                    "v0.1",
                    request.created_by,
                    request.created_by,
                    request.remarks,
                ),
            )
            result_id = cursor.lastrowid

            detail_rows = []
            for item in phase_income_details:
                detail_rows.append(
                    (
                        result_id,
                        item["product_code"],
                        item["product_name"],
                        item["category_code"],
                        str(item["split_ratio"]),
                        str(item["tax_included_amount"]),
                        str(item["tax_excluded_amount"]),
                        item["sort_order"],
                        item["remarks"],
                    )
                )

            cursor.executemany(
                """
                INSERT INTO result_storage_detail
                (
                    result_id, product_code, product_name, category_code,
                    split_ratio, tax_included_amount, tax_excluded_amount,
                    sort_order, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                detail_rows,
            )

            workflow_ext = {
                "source_record_type": "phase_income_record",
                "source_record_id": phase_income_record["id"],
                "result_code": result_code,
            }

            cursor.execute(
                """
                INSERT INTO workflow_status_log
                (
                    business_key, business_type, source_module,
                    from_status, to_status,
                    action_type, operator, action_time,
                    related_record_type, related_record_id,
                    message, ext_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    phase_income_record["phase_income_code"],
                    "PHASE_INCOME",
                    "result_storage",
                    phase_income_record["calc_status"],
                    "RESULT_STORED",
                    "STORE",
                    request.created_by,
                    datetime.utcnow().isoformat(),
                    "result_storage_record",
                    result_id,
                    "phase income result stored successfully",
                    self._dump_json(workflow_ext),
                ),
            )

            conn.commit()

        return self.get_result_record(result_id)

    def get_result_record(self, result_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, result_code, source_record_type, source_record_id,
                    billing_period, billing_date,
                    project_code, project_name,
                    contract_id, contract_code, contract_name,
                    rule_id, rule_code, rule_name,
                    input_amount, amount_type,
                    tax_included_amount, tax_excluded_amount, tax_rate,
                    result_status, version_no,
                    created_at, updated_at, created_by, updated_by, remarks
                FROM result_storage_record
                WHERE id = ?
                """,
                (result_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="result storage record not found")

            details = self._get_result_details(result_id, conn)

            return {
                "id": row["id"],
                "result_code": row["result_code"],
                "source_record_type": row["source_record_type"],
                "source_record_id": row["source_record_id"],
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
                "result_status": row["result_status"],
                "version_no": row["version_no"],
                "created_at": self._parse_datetime(row["created_at"]),
                "updated_at": self._parse_datetime(row["updated_at"]),
                "created_by": row["created_by"],
                "updated_by": row["updated_by"],
                "remarks": row["remarks"],
                "details": details,
            }

    # ============================================================
    # Workflow Status Log
    # ============================================================
    def create_workflow_status_log(self, request: WorkflowStatusLogCreateRequest) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO workflow_status_log
                (
                    business_key, business_type, source_module,
                    from_status, to_status,
                    action_type, operator, action_time,
                    related_record_type, related_record_id,
                    message, ext_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.business_key,
                    request.business_type,
                    request.source_module,
                    request.from_status,
                    request.to_status,
                    request.action_type,
                    request.operator,
                    datetime.utcnow().isoformat(),
                    request.related_record_type,
                    request.related_record_id,
                    request.message,
                    self._dump_json(request.ext_json),
                ),
            )
            log_id = cursor.lastrowid
            conn.commit()

        return self.get_workflow_status_log(log_id)

    def get_workflow_status_log(self, log_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, business_key, business_type, source_module,
                    from_status, to_status,
                    action_type, operator, action_time,
                    related_record_type, related_record_id,
                    message, ext_json
                FROM workflow_status_log
                WHERE id = ?
                """,
                (log_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="workflow status log not found")

            return {
                "id": row["id"],
                "business_key": row["business_key"],
                "business_type": row["business_type"],
                "source_module": row["source_module"],
                "from_status": row["from_status"],
                "to_status": row["to_status"],
                "action_type": row["action_type"],
                "operator": row["operator"],
                "action_time": self._parse_datetime(row["action_time"]),
                "related_record_type": row["related_record_type"],
                "related_record_id": row["related_record_id"],
                "message": row["message"],
                "ext_json": self._load_json(row["ext_json"]),
            }

    def list_workflow_status_logs(
        self,
        business_key: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, business_key, business_type, source_module,
                    from_status, to_status,
                    action_type, operator, action_time,
                    related_record_type, related_record_id,
                    message, ext_json
                FROM workflow_status_log
                WHERE business_key = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (business_key, limit),
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "id": row["id"],
                        "business_key": row["business_key"],
                        "business_type": row["business_type"],
                        "source_module": row["source_module"],
                        "from_status": row["from_status"],
                        "to_status": row["to_status"],
                        "action_type": row["action_type"],
                        "operator": row["operator"],
                        "action_time": self._parse_datetime(row["action_time"]),
                        "related_record_type": row["related_record_type"],
                        "related_record_id": row["related_record_id"],
                        "message": row["message"],
                        "ext_json": self._load_json(row["ext_json"]),
                    }
                )
            return results

    # ============================================================
    # Internal Payload
    # ============================================================
    def build_result_internal_payload(self, result_id: int) -> Dict[str, Any]:
        record = self.get_result_record(result_id)

        return {
            "record_type": "result_storage_record",
            "record_id": record["id"],
            "business_key": record["result_code"],
            "status": record["result_status"],
            "next_step": "QUERY_DISPLAY",
            "payload": {
                "result_code": record["result_code"],
                "source_record_type": record["source_record_type"],
                "source_record_id": record["source_record_id"],
                "billing_period": record["billing_period"],
                "billing_date": str(record["billing_date"]) if record["billing_date"] else None,
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
            },
            "warnings": [],
            "trace": {
                "module": "result_storage",
                "reserved_for": ["query_display"],
            },
        }

    # ============================================================
    # Internal Query Helpers
    # ============================================================
    def _get_phase_income_record(self, record_id: int) -> Dict[str, Any]:
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
            }

    def _get_phase_income_details(self, record_id: int) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
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

    def _get_result_details(self, result_id: int, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, result_id, product_code, product_name, category_code,
                split_ratio, tax_included_amount, tax_excluded_amount,
                sort_order, created_at, updated_at, remarks
            FROM result_storage_detail
            WHERE result_id = ?
            ORDER BY sort_order, id
            """,
            (result_id,),
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "result_id": row["result_id"],
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

    def _find_existing_result_by_source(
        self,
        source_record_type: str,
        source_record_id: int,
    ) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, result_code
                FROM result_storage_record
                WHERE source_record_type = ? AND source_record_id = ?
                LIMIT 1
                """,
                (source_record_type, source_record_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "result_code": row["result_code"],
            }

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