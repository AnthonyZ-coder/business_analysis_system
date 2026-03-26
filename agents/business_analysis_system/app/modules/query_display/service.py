import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.core.config import DB_PATH
from app.modules.query_display.schemas import (
    ProjectSummaryQueryRequest,
    ResultListQueryRequest,
    WorkflowQueryRequest,
)


class QueryDisplayService:
    """
    query_display module service

    Current MVP responsibilities:
    - list result storage records
    - get result storage record detail
    - build dynamic category summary from result details
    - list workflow logs
    - build project monthly summary
    """

    def __init__(self) -> None:
        self.db_path = str(DB_PATH)

    # ============================================================
    # Result List
    # ============================================================
    def list_results(self, request: ResultListQueryRequest) -> List[Dict[str, Any]]:
        conditions = []
        params: List[Any] = []

        if request.billing_period:
            conditions.append("billing_period = ?")
            params.append(request.billing_period)

        if request.project_code:
            conditions.append("project_code = ?")
            params.append(request.project_code)

        if request.project_name:
            conditions.append("project_name LIKE ?")
            params.append(f"%{request.project_name}%")

        if request.contract_code:
            conditions.append("contract_code LIKE ?")
            params.append(f"%{request.contract_code}%")

        if request.contract_name:
            conditions.append("contract_name LIKE ?")
            params.append(f"%{request.contract_name}%")

        if request.rule_name:
            conditions.append("rule_name LIKE ?")
            params.append(f"%{request.rule_name}%")

        if request.result_status:
            conditions.append("result_status = ?")
            params.append(request.result_status)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        params.append(request.limit)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT
                    id, result_code,
                    billing_period, billing_date,
                    project_code, project_name,
                    contract_id, contract_code, contract_name,
                    rule_id, rule_code, rule_name,
                    amount_type, tax_included_amount, tax_excluded_amount,
                    result_status, created_at, updated_at
                FROM result_storage_record
                {where_clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "result_id": row["id"],
                        "result_code": row["result_code"],
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
                        "amount_type": row["amount_type"],
                        "tax_included_amount": self._to_decimal_required(row["tax_included_amount"]),
                        "tax_excluded_amount": self._to_decimal_required(row["tax_excluded_amount"]),
                        "result_status": row["result_status"],
                        "created_at": self._parse_datetime(row["created_at"]),
                        "updated_at": self._parse_datetime(row["updated_at"]),
                    }
                )
            return results

    # ============================================================
    # Result Detail
    # ============================================================
    def get_result_detail(self, result_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, result_code,
                    source_record_type, source_record_id,
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
            category_summary = self._build_category_summary(details)
            workflow_logs = self._get_workflow_logs_by_result_record(
                result_id=result_id,
                source_record_type=row["source_record_type"],
                source_record_id=row["source_record_id"],
                conn=conn,
            )

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
                "category_summary": category_summary,
                "workflow_logs": workflow_logs,
            }

    # ============================================================
    # Project Summary
    # ============================================================
    def get_project_summary(self, request: ProjectSummaryQueryRequest) -> List[Dict[str, Any]]:
        conditions = []
        params: List[Any] = []

        if request.billing_period:
            conditions.append("r.billing_period = ?")
            params.append(request.billing_period)

        if request.project_code:
            conditions.append("r.project_code = ?")
            params.append(request.project_code)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        params.append(request.limit)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT
                    r.billing_period,
                    r.project_code,
                    r.project_name,
                    COUNT(*) AS result_count,
                    SUM(CAST(r.tax_included_amount AS REAL)) AS total_tax_included_amount,
                    SUM(CAST(r.tax_excluded_amount AS REAL)) AS total_tax_excluded_amount
                FROM result_storage_record r
                {where_clause}
                GROUP BY r.billing_period, r.project_code, r.project_name
                ORDER BY r.billing_period DESC, r.project_code ASC
                LIMIT ?
                """,
                params,
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                category_summary = self._get_project_category_summary(
                    billing_period=row["billing_period"],
                    project_code=row["project_code"],
                    conn=conn,
                )

                results.append(
                    {
                        "billing_period": row["billing_period"],
                        "project_code": row["project_code"],
                        "project_name": row["project_name"],
                        "result_count": row["result_count"],
                        "total_tax_included_amount": self._quantize_money(row["total_tax_included_amount"] or 0),
                        "total_tax_excluded_amount": self._quantize_money(row["total_tax_excluded_amount"] or 0),
                        "category_summary": category_summary,
                    }
                )

            return results

    # ============================================================
    # Workflow Logs
    # ============================================================
    def list_workflow_logs(self, request: WorkflowQueryRequest) -> List[Dict[str, Any]]:
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
                (request.business_key, request.limit),
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
    def build_result_query_payload(self, result_id: int) -> Dict[str, Any]:
        record = self.get_result_detail(result_id)

        return {
            "record_type": "query_display_result",
            "record_id": record["id"],
            "business_key": record["result_code"],
            "status": record["result_status"],
            "next_step": None,
            "payload": record,
            "warnings": [],
            "trace": {
                "module": "query_display",
                "reserved_for": [],
            },
        }

    # ============================================================
    # Internal Query Helpers
    # ============================================================
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

    def _build_category_summary(self, details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        category_map: Dict[str, Dict[str, Any]] = {}

        for item in details:
            category_code = item["category_code"]
            if category_code not in category_map:
                category_map[category_code] = {
                    "category_code": category_code,
                    "category_name": self._get_category_name(category_code),
                    "split_ratio": Decimal("0"),
                    "tax_included_amount": Decimal("0"),
                    "tax_excluded_amount": Decimal("0"),
                }

            category_map[category_code]["split_ratio"] += self._to_decimal_required(item["split_ratio"])
            category_map[category_code]["tax_included_amount"] += self._to_decimal_required(item["tax_included_amount"])
            category_map[category_code]["tax_excluded_amount"] += self._to_decimal_required(item["tax_excluded_amount"])

        results = []
        for _, value in category_map.items():
            results.append(
                {
                    "category_code": value["category_code"],
                    "category_name": value["category_name"],
                    "split_ratio": self._quantize_ratio(value["split_ratio"]),
                    "tax_included_amount": self._quantize_money(value["tax_included_amount"]),
                    "tax_excluded_amount": self._quantize_money(value["tax_excluded_amount"]),
                }
            )

        results.sort(key=lambda x: x["category_code"])
        return results

    def _get_project_category_summary(
        self,
        billing_period: str,
        project_code: str,
        conn: sqlite3.Connection,
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                d.category_code,
                SUM(CAST(d.split_ratio AS REAL)) AS split_ratio,
                SUM(CAST(d.tax_included_amount AS REAL)) AS tax_included_amount,
                SUM(CAST(d.tax_excluded_amount AS REAL)) AS tax_excluded_amount
            FROM result_storage_record r
            JOIN result_storage_detail d ON r.id = d.result_id
            WHERE r.billing_period = ? AND r.project_code = ?
            GROUP BY d.category_code
            ORDER BY d.category_code
            """,
            (billing_period, project_code),
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            category_code = row["category_code"]
            results.append(
                {
                    "category_code": category_code,
                    "category_name": self._get_category_name(category_code),
                    "split_ratio": self._quantize_ratio(row["split_ratio"] or 0),
                    "tax_included_amount": self._quantize_money(row["tax_included_amount"] or 0),
                    "tax_excluded_amount": self._quantize_money(row["tax_excluded_amount"] or 0),
                }
            )
        return results

    def _get_workflow_logs_by_result_record(
        self,
        result_id: int,
        source_record_type: str,
        source_record_id: int,
        conn: sqlite3.Connection,
    ) -> List[Dict[str, Any]]:
        # 当前第一阶段，优先按 result_storage_record 关联日志查
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
            WHERE
                (related_record_type = 'result_storage_record' AND related_record_id = ?)
                OR (related_record_type = ? AND related_record_id = ?)
            ORDER BY id DESC
            """,
            (result_id, source_record_type, source_record_id),
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

    def _quantize_money(self, value: Any) -> Decimal:
        value = self._to_decimal_required(value)
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _quantize_ratio(self, value: Any) -> Decimal:
        value = self._to_decimal_required(value)
        return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)