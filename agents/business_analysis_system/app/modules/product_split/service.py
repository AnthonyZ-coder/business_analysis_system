import json
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from app.core.config import DB_PATH
from app.modules.product_split.schemas import (
    ProductSplitDraftCreateRequest,
    ProductSplitDraftSubmitRequest,
    ProductSplitDraftUpdateRequest,
    ProductSplitSuggestionCreateRequest,
    ProjectSplitRuleBindingCreateRequest,
)


class ProductSplitService:
    """
    product_split module service

    Current MVP responsibilities:
    - create / query suggestion
    - create / query / update draft
    - submit draft to rule
    - bind project to rule
    - build downstream payload
    """

    def __init__(self) -> None:
        self.db_path = str(DB_PATH)

    # ============================================================
    # Suggestion
    # ============================================================
    def create_suggestion(self, request: ProductSplitSuggestionCreateRequest) -> Dict[str, Any]:
        self._validate_project_code_exists(request.project_code)
        if request.contract_id is not None:
            self._validate_contract_exists(request.contract_id)

        self._validate_split_detail_items(request.details)

        suggestion_code = self._generate_code("SUG")
        category_split_json = self._normalize_category_split_json(request.category_split_json)
        reference_case_ids = self._dump_json(request.reference_case_ids or [])

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO product_split_suggestion
                (
                    suggestion_code, project_code, contract_id, contract_code, suggestion_name,
                    source_type, source_model, llm_enabled_flag, category_split_json,
                    evidence_summary, reference_case_ids, matrix_applied_flag,
                    review_status, status, version_no, created_by, updated_by, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    suggestion_code,
                    request.project_code,
                    request.contract_id,
                    request.contract_code,
                    request.suggestion_name,
                    request.source_type,
                    request.source_model,
                    request.llm_enabled_flag,
                    self._dump_json(category_split_json),
                    request.evidence_summary,
                    reference_case_ids,
                    request.matrix_applied_flag,
                    "GENERATED",
                    "ENABLED",
                    "v0.1",
                    request.created_by,
                    request.created_by,
                    request.remarks,
                ),
            )
            suggestion_id = cursor.lastrowid

            detail_rows = []
            for index, item in enumerate(request.details, start=1):
                product_info = self._get_product_line_definition(item.product_code, conn)
                detail_rows.append(
                    (
                        suggestion_id,
                        product_info["product_code"],
                        product_info["product_name"],
                        product_info["category_code"],
                        str(self._to_decimal_required(item.split_ratio)),
                        None,
                        request.source_type,
                        None,
                        None,
                        None,
                        index,
                        item.remarks,
                    )
                )

            if detail_rows:
                cursor.executemany(
                    """
                    INSERT INTO product_split_suggestion_detail
                    (
                        suggestion_id, product_code, product_name, category_code,
                        split_ratio, confidence_score, source_type,
                        evidence_text, evidence_page_info, matrix_weight,
                        sort_order, remarks
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    detail_rows,
                )

            conn.commit()

        return self.get_suggestion(suggestion_id)

    def get_suggestion(self, suggestion_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, suggestion_code, project_code, contract_id, contract_code, suggestion_name,
                    source_type, source_model, llm_enabled_flag, category_split_json,
                    evidence_summary, reference_case_ids, matrix_applied_flag,
                    review_status, reviewer, reviewed_at, status, version_no,
                    created_at, updated_at, created_by, updated_by, remarks
                FROM product_split_suggestion
                WHERE id = ?
                """,
                (suggestion_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="product split suggestion not found")

            detail_rows = self._get_suggestion_details(suggestion_id, conn)

            return {
                "id": row["id"],
                "suggestion_code": row["suggestion_code"],
                "project_code": row["project_code"],
                "contract_id": row["contract_id"],
                "contract_code": row["contract_code"],
                "suggestion_name": row["suggestion_name"],
                "source_type": row["source_type"],
                "source_model": row["source_model"],
                "llm_enabled_flag": row["llm_enabled_flag"],
                "category_split_json": self._load_json(row["category_split_json"]),
                "evidence_summary": row["evidence_summary"],
                "reference_case_ids": row["reference_case_ids"],
                "matrix_applied_flag": row["matrix_applied_flag"],
                "review_status": row["review_status"],
                "reviewer": row["reviewer"],
                "reviewed_at": self._parse_datetime(row["reviewed_at"]),
                "status": row["status"],
                "version_no": row["version_no"],
                "created_at": self._parse_datetime(row["created_at"]),
                "updated_at": self._parse_datetime(row["updated_at"]),
                "created_by": row["created_by"],
                "updated_by": row["updated_by"],
                "remarks": row["remarks"],
                "details": detail_rows,
            }

    # ============================================================
    # Draft
    # ============================================================
    def create_draft(self, request: ProductSplitDraftCreateRequest) -> Dict[str, Any]:
        self._validate_project_code_exists(request.project_code)
        if request.contract_id is not None:
            self._validate_contract_exists(request.contract_id)

        if request.from_suggestion_id is not None:
            self._validate_suggestion_exists(request.from_suggestion_id)

        self._validate_split_detail_items(request.details)

        draft_code = self._generate_code("DRF")
        category_split_json = self._normalize_category_split_json(request.category_split_json)

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO product_split_rule_draft
                (
                    draft_code, project_code, contract_id, contract_code, draft_name,
                    draft_source_type, llm_enabled_flag, from_suggestion_id,
                    category_split_json, edit_status, review_status, status, version_no,
                    created_by, updated_by, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft_code,
                    request.project_code,
                    request.contract_id,
                    request.contract_code,
                    request.draft_name,
                    request.draft_source_type,
                    request.llm_enabled_flag,
                    request.from_suggestion_id,
                    self._dump_json(category_split_json),
                    "DRAFT",
                    "DRAFT",
                    "ENABLED",
                    "v0.1",
                    request.created_by,
                    request.created_by,
                    request.remarks,
                ),
            )
            draft_id = cursor.lastrowid

            detail_rows = []
            for index, item in enumerate(request.details, start=1):
                product_info = self._get_product_line_definition(item.product_code, conn)
                detail_rows.append(
                    (
                        draft_id,
                        product_info["product_code"],
                        product_info["product_name"],
                        product_info["category_code"],
                        str(self._to_decimal_required(item.split_ratio)),
                        "MANUAL" if request.from_suggestion_id is None else "FROM_SUGGESTION",
                        None,
                        item.adjust_reason,
                        index,
                        item.remarks,
                    )
                )

            cursor.executemany(
                """
                INSERT INTO product_split_rule_draft_detail
                (
                    draft_id, product_code, product_name, category_code,
                    split_ratio, source_type, based_suggestion_detail_id,
                    adjust_reason, sort_order, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                detail_rows,
            )

            conn.commit()

        return self.get_draft(draft_id)

    def get_draft(self, draft_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, draft_code, project_code, contract_id, contract_code, draft_name,
                    draft_source_type, llm_enabled_flag, from_suggestion_id,
                    category_split_json, edit_status, review_status, reviewer,
                    reviewed_at, status, version_no, created_at, updated_at,
                    created_by, updated_by, remarks
                FROM product_split_rule_draft
                WHERE id = ?
                """,
                (draft_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="product split rule draft not found")

            detail_rows = self._get_draft_details(draft_id, conn)

            return {
                "id": row["id"],
                "draft_code": row["draft_code"],
                "project_code": row["project_code"],
                "contract_id": row["contract_id"],
                "contract_code": row["contract_code"],
                "draft_name": row["draft_name"],
                "draft_source_type": row["draft_source_type"],
                "llm_enabled_flag": row["llm_enabled_flag"],
                "from_suggestion_id": row["from_suggestion_id"],
                "category_split_json": self._load_json(row["category_split_json"]),
                "edit_status": row["edit_status"],
                "review_status": row["review_status"],
                "reviewer": row["reviewer"],
                "reviewed_at": self._parse_datetime(row["reviewed_at"]),
                "status": row["status"],
                "version_no": row["version_no"],
                "created_at": self._parse_datetime(row["created_at"]),
                "updated_at": self._parse_datetime(row["updated_at"]),
                "created_by": row["created_by"],
                "updated_by": row["updated_by"],
                "remarks": row["remarks"],
                "details": detail_rows,
            }

    def update_draft(self, draft_id: int, request: ProductSplitDraftUpdateRequest) -> Dict[str, Any]:
        current = self.get_draft(draft_id)

        if request.details is not None:
            self._validate_split_detail_items(request.details)

        new_draft_name = request.draft_name if request.draft_name is not None else current["draft_name"]
        new_category_split_json = (
            self._normalize_category_split_json(request.category_split_json)
            if request.category_split_json is not None
            else current["category_split_json"]
        )
        new_remarks = request.remarks if request.remarks is not None else current["remarks"]

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE product_split_rule_draft
                SET draft_name = ?, category_split_json = ?, edit_status = ?, updated_by = ?, remarks = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    new_draft_name,
                    self._dump_json(new_category_split_json),
                    "EDITING",
                    request.updated_by,
                    new_remarks,
                    draft_id,
                ),
            )

            if request.details is not None:
                cursor.execute(
                    "DELETE FROM product_split_rule_draft_detail WHERE draft_id = ?",
                    (draft_id,),
                )

                detail_rows = []
                for index, item in enumerate(request.details, start=1):
                    product_info = self._get_product_line_definition(item.product_code, conn)
                    detail_rows.append(
                        (
                            draft_id,
                            product_info["product_code"],
                            product_info["product_name"],
                            product_info["category_code"],
                            str(self._to_decimal_required(item.split_ratio)),
                            "MANUAL",
                            None,
                            item.adjust_reason,
                            index,
                            item.remarks,
                        )
                    )

                cursor.executemany(
                    """
                    INSERT INTO product_split_rule_draft_detail
                    (
                        draft_id, product_code, product_name, category_code,
                        split_ratio, source_type, based_suggestion_detail_id,
                        adjust_reason, sort_order, remarks
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    detail_rows,
                )

            conn.commit()

        return self.get_draft(draft_id)

    def submit_draft_to_rule(self, draft_id: int, request: ProductSplitDraftSubmitRequest) -> Dict[str, Any]:
        draft = self.get_draft(draft_id)
        if not draft["details"]:
            raise HTTPException(status_code=400, detail="draft details cannot be empty")

        # 1. 对 draft 明细做最终校验
        self._validate_existing_draft_details(draft["details"])

        # 2. 自动汇总六大类比例
        category_split_json = self._build_category_split_json(draft["details"])

        rule_code = self._generate_code("RUL")

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO product_split_rule
                (
                    rule_code, rule_name, rule_type, project_type_tag, applicable_scope,
                    category_split_json, source_draft_id, review_status, reviewer,
                    reviewed_at, is_default, status, version_no, created_by, updated_by, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rule_code,
                    request.rule_name,
                    request.rule_type,
                    request.project_type_tag,
                    request.applicable_scope,
                    self._dump_json(category_split_json),
                    draft_id,
                    "APPROVED",
                    request.reviewer,
                    datetime.utcnow().isoformat(),
                    0,
                    "ENABLED",
                    "v0.1",
                    request.created_by,
                    request.created_by,
                    request.remarks,
                ),
            )
            rule_id = cursor.lastrowid

            cursor.execute(
                """
                SELECT
                    id, product_code, product_name, category_code, split_ratio, sort_order, remarks
                FROM product_split_rule_draft_detail
                WHERE draft_id = ?
                ORDER BY sort_order, id
                """,
                (draft_id,),
            )
            draft_detail_rows = cursor.fetchall()

            rule_detail_rows = []
            for row in draft_detail_rows:
                rule_detail_rows.append(
                    (
                        rule_id,
                        row["product_code"],
                        row["product_name"],
                        row["category_code"],
                        row["split_ratio"],
                        "FROM_DRAFT",
                        row["id"],
                        row["sort_order"],
                        row["remarks"],
                    )
                )

            cursor.executemany(
                """
                INSERT INTO product_split_rule_detail
                (
                    rule_id, product_code, product_name, category_code,
                    split_ratio, source_type, based_draft_detail_id,
                    sort_order, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rule_detail_rows,
            )

            # 3. 回写 draft 的 category_split_json 和状态
            cursor.execute(
                """
                UPDATE product_split_rule_draft
                SET category_split_json = ?, edit_status = ?, review_status = ?, reviewer = ?, reviewed_at = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    self._dump_json(category_split_json),
                    "SUBMITTED",
                    "APPROVED",
                    request.reviewer,
                    datetime.utcnow().isoformat(),
                    request.created_by,
                    draft_id,
                ),
            )

            conn.commit()

        return self.get_rule(rule_id)

    # ============================================================
    # Rule
    # ============================================================
    def get_rule(self, rule_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, rule_code, rule_name, rule_type, project_type_tag, applicable_scope,
                    category_split_json, source_draft_id, review_status, reviewer, reviewed_at,
                    is_default, status, version_no, created_at, updated_at, created_by, updated_by, remarks
                FROM product_split_rule
                WHERE id = ?
                """,
                (rule_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="product split rule not found")

            detail_rows = self._get_rule_details(rule_id, conn)

            return {
                "id": row["id"],
                "rule_code": row["rule_code"],
                "rule_name": row["rule_name"],
                "rule_type": row["rule_type"],
                "project_type_tag": row["project_type_tag"],
                "applicable_scope": row["applicable_scope"],
                "category_split_json": self._load_json(row["category_split_json"]),
                "source_draft_id": row["source_draft_id"],
                "review_status": row["review_status"],
                "reviewer": row["reviewer"],
                "reviewed_at": self._parse_datetime(row["reviewed_at"]),
                "is_default": row["is_default"],
                "status": row["status"],
                "version_no": row["version_no"],
                "created_at": self._parse_datetime(row["created_at"]),
                "updated_at": self._parse_datetime(row["updated_at"]),
                "created_by": row["created_by"],
                "updated_by": row["updated_by"],
                "remarks": row["remarks"],
                "details": detail_rows,
            }

    # ============================================================
    # Binding
    # ============================================================
    def create_project_rule_binding(self, request: ProjectSplitRuleBindingCreateRequest) -> Dict[str, Any]:
        self._validate_project_code_exists(request.project_code)
        self._validate_rule_exists(request.rule_id)

        if request.contract_id is not None:
            self._validate_contract_exists(request.contract_id)

        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE project_split_rule_binding
                SET binding_status = 'INACTIVE', updated_at = CURRENT_TIMESTAMP
                WHERE project_code = ? AND binding_status = 'ACTIVE'
                """,
                (request.project_code,),
            )

            cursor.execute(
                """
                INSERT INTO project_split_rule_binding
                (
                    project_code, contract_id, contract_code, rule_id, binding_status,
                    selected_by, selected_at, effective_from, effective_to, remarks
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.project_code,
                    request.contract_id,
                    request.contract_code,
                    request.rule_id,
                    "ACTIVE",
                    request.selected_by,
                    datetime.utcnow().isoformat(),
                    request.effective_from.isoformat() if request.effective_from else None,
                    request.effective_to.isoformat() if request.effective_to else None,
                    request.remarks,
                ),
            )
            binding_id = cursor.lastrowid
            conn.commit()

        return self.get_project_rule_binding(binding_id)

    def get_project_rule_binding(self, binding_id: int) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id, project_code, contract_id, contract_code, rule_id, binding_status,
                    selected_by, selected_at, effective_from, effective_to,
                    created_at, updated_at, remarks
                FROM project_split_rule_binding
                WHERE id = ?
                """,
                (binding_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="project split rule binding not found")

            return {
                "id": row["id"],
                "project_code": row["project_code"],
                "contract_id": row["contract_id"],
                "contract_code": row["contract_code"],
                "rule_id": row["rule_id"],
                "binding_status": row["binding_status"],
                "selected_by": row["selected_by"],
                "selected_at": self._parse_datetime(row["selected_at"]),
                "effective_from": self._parse_datetime(row["effective_from"]),
                "effective_to": self._parse_datetime(row["effective_to"]),
                "created_at": self._parse_datetime(row["created_at"]),
                "updated_at": self._parse_datetime(row["updated_at"]),
                "remarks": row["remarks"],
            }

    # ============================================================
    # Internal Payload
    # ============================================================
    def build_rule_internal_payload(self, rule_id: int) -> Dict[str, Any]:
        rule = self.get_rule(rule_id)

        return {
            "record_type": "product_split_rule",
            "record_id": rule["id"],
            "business_key": rule["rule_code"],
            "status": rule["status"],
            "next_step": "PHASE_INCOME_CALC",
            "payload": {
                "rule_code": rule["rule_code"],
                "rule_name": rule["rule_name"],
                "rule_type": rule["rule_type"],
                "project_type_tag": rule["project_type_tag"],
                "applicable_scope": rule["applicable_scope"],
                "category_split_json": rule["category_split_json"],
                "details": [
                    {
                        "product_code": item["product_code"],
                        "product_name": item["product_name"],
                        "category_code": item["category_code"],
                        "split_ratio": str(item["split_ratio"]),
                    }
                    for item in rule["details"]
                ],
            },
            "warnings": [],
            "trace": {
                "module": "product_split",
                "reserved_for": ["phase_income_calc"],
            },
        }

    # ============================================================
    # Internal Query Helpers
    # ============================================================
    def _get_suggestion_details(self, suggestion_id: int, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, suggestion_id, product_code, product_name, category_code, split_ratio,
                confidence_score, source_type, evidence_text, evidence_page_info,
                matrix_weight, sort_order, created_at, updated_at, remarks
            FROM product_split_suggestion_detail
            WHERE suggestion_id = ?
            ORDER BY sort_order, id
            """,
            (suggestion_id,),
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "suggestion_id": row["suggestion_id"],
                    "product_code": row["product_code"],
                    "product_name": row["product_name"],
                    "category_code": row["category_code"],
                    "split_ratio": self._to_decimal(row["split_ratio"]),
                    "confidence_score": self._to_decimal(row["confidence_score"]),
                    "source_type": row["source_type"],
                    "evidence_text": row["evidence_text"],
                    "evidence_page_info": row["evidence_page_info"],
                    "matrix_weight": self._to_decimal(row["matrix_weight"]),
                    "sort_order": row["sort_order"],
                    "created_at": self._parse_datetime(row["created_at"]),
                    "updated_at": self._parse_datetime(row["updated_at"]),
                    "remarks": row["remarks"],
                }
            )
        return results

    def _get_draft_details(self, draft_id: int, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, draft_id, product_code, product_name, category_code, split_ratio,
                source_type, based_suggestion_detail_id, adjust_reason,
                sort_order, created_at, updated_at, remarks
            FROM product_split_rule_draft_detail
            WHERE draft_id = ?
            ORDER BY sort_order, id
            """,
            (draft_id,),
        )
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "draft_id": row["draft_id"],
                    "product_code": row["product_code"],
                    "product_name": row["product_name"],
                    "category_code": row["category_code"],
                    "split_ratio": self._to_decimal(row["split_ratio"]),
                    "source_type": row["source_type"],
                    "based_suggestion_detail_id": row["based_suggestion_detail_id"],
                    "adjust_reason": row["adjust_reason"],
                    "sort_order": row["sort_order"],
                    "created_at": self._parse_datetime(row["created_at"]),
                    "updated_at": self._parse_datetime(row["updated_at"]),
                    "remarks": row["remarks"],
                }
            )
        return results

    def _get_rule_details(self, rule_id: int, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, rule_id, product_code, product_name, category_code, split_ratio,
                source_type, based_draft_detail_id, sort_order,
                created_at, updated_at, remarks
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
                    "split_ratio": self._to_decimal(row["split_ratio"]),
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

    def _validate_contract_exists(self, contract_id: int) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM contract_info WHERE id = ?", (contract_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="contract_id does not exist")

    def _validate_suggestion_exists(self, suggestion_id: int) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM product_split_suggestion WHERE id = ?", (suggestion_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="from_suggestion_id does not exist")

    def _validate_rule_exists(self, rule_id: int) -> None:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM product_split_rule WHERE id = ?", (rule_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="rule_id does not exist")

    def _get_product_line_definition(self, product_code: str, conn: sqlite3.Connection) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT product_code, product_name, category_code
            FROM product_line_definition
            WHERE product_code = ? AND status = 'ENABLED'
            """,
            (product_code,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail=f"product_code does not exist or is disabled: {product_code}")

        return {
            "product_code": row["product_code"],
            "product_name": row["product_name"],
            "category_code": row["category_code"],
        }

    def _validate_split_detail_items(self, detail_items: List[Any]) -> None:
        if not detail_items:
            raise HTTPException(status_code=400, detail="details cannot be empty")

        seen_product_codes = set()
        total_ratio = Decimal("0")

        for item in detail_items:
            product_code = item.product_code
            split_ratio = self._to_decimal_required(item.split_ratio)

            if product_code in seen_product_codes:
                raise HTTPException(status_code=400, detail=f"duplicate product_code found: {product_code}")
            seen_product_codes.add(product_code)

            if split_ratio < Decimal("0") or split_ratio > Decimal("1"):
                raise HTTPException(status_code=400, detail=f"split_ratio out of range for product_code: {product_code}")

            total_ratio += split_ratio

        if abs(total_ratio - Decimal("1")) > Decimal("0.0001"):
            raise HTTPException(status_code=400, detail="sum of details.split_ratio must be 1")

    def _validate_existing_draft_details(self, detail_rows: List[Dict[str, Any]]) -> None:
        if not detail_rows:
            raise HTTPException(status_code=400, detail="draft details cannot be empty")

        seen_product_codes = set()
        total_ratio = Decimal("0")

        for item in detail_rows:
            product_code = item["product_code"]
            split_ratio = self._to_decimal_required(item["split_ratio"])

            if product_code in seen_product_codes:
                raise HTTPException(status_code=400, detail=f"duplicate product_code found in draft: {product_code}")
            seen_product_codes.add(product_code)

            if split_ratio < Decimal("0") or split_ratio > Decimal("1"):
                raise HTTPException(status_code=400, detail=f"split_ratio out of range in draft for product_code: {product_code}")

            total_ratio += split_ratio

        if abs(total_ratio - Decimal("1")) > Decimal("0.0001"):
            raise HTTPException(status_code=400, detail="sum of draft detail split_ratio must be 1")

    def _build_category_split_json(self, detail_rows: List[Dict[str, Any]]) -> Dict[str, str]:
        category_map: Dict[str, Decimal] = {}

        for item in detail_rows:
            category_code = item["category_code"]
            split_ratio = self._to_decimal_required(item["split_ratio"])

            if category_code not in category_map:
                category_map[category_code] = Decimal("0")

            category_map[category_code] += split_ratio

        total_ratio = sum(category_map.values(), Decimal("0"))
        if abs(total_ratio - Decimal("1")) > Decimal("0.0001"):
            raise HTTPException(status_code=400, detail="sum of category split ratio must be 1")

        return {key: str(value) for key, value in category_map.items()}

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

    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _to_decimal_required(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"invalid decimal value: {value}")

    def _normalize_category_split_json(
        self,
        category_split_json: Optional[Dict[str, Decimal]],
    ) -> Optional[Dict[str, str]]:
        if category_split_json is None:
            return None

        normalized: Dict[str, str] = {}
        total = Decimal("0")

        for key, value in category_split_json.items():
            decimal_value = self._to_decimal_required(value)
            if decimal_value < Decimal("0") or decimal_value > Decimal("1"):
                raise HTTPException(status_code=400, detail=f"category split ratio out of range: {key}")

            normalized[key] = str(decimal_value)
            total += decimal_value

        if abs(total - Decimal("1")) > Decimal("0.0001"):
            raise HTTPException(status_code=400, detail="sum of category_split_json ratios must be 1")

        return normalized