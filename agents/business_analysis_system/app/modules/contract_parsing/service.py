from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.common.enums import NextStep, ParseStatus
from app.models.billing_record import BillingRecord
from app.models.contract_info import ContractInfo
from app.models.file_record import FileRecord
from app.modules.contract_parsing.schemas import (
    ContractParseAdjustRequest,
    ParseRequest,
)
from app.modules.contract_parsing.utils import (
    dump_json_text,
    extract_text_from_pdf,
    load_json_text,
    merge_dict,
    safe_text_preview,
)


ALLOWED_ADJUST_FIELDS = [
    "contract_code",
    "contract_name",
    "project_code",
    "customer_name",
    "contract_amount",
    "sign_date",
]


def _normalize_adjust_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class ContractParsingService:
    """
    Contract parsing module service.

    Current MVP responsibilities:
    - read contract / billing PDF files from file_record
    - extract raw text from PDF files
    - persist parsing result into ext_json
    - update parse statuses
    - provide downstream module payloads
    - allow manual adjustment for parsed contract fields
    - record adjustment logs
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # Contract
    # ============================================================
    def parse_contract(self, contract_id: int, request: ParseRequest) -> Dict[str, Any]:
        contract = self.get_contract(contract_id)

        if not contract.file_record_id:
            raise HTTPException(status_code=400, detail="contract has no linked file_record_id")

        file_record = self.get_file_record(contract.file_record_id)

        if not request.force_reparse and contract.parse_status == ParseStatus.SUCCESS.value:
            return self.get_contract_parse_result(contract_id)

        try:
            extracted_text, extracted_page_count, warnings = extract_text_from_pdf(
                file_path=file_record.storage_path,
                max_pages=request.max_pages,
            )
        except FileNotFoundError as exc:
            self._mark_contract_parse_failed(contract, file_record, str(exc))
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ModuleNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail="pypdf is not installed. Please install dependency first.",
            ) from exc
        except Exception as exc:
            self._mark_contract_parse_failed(contract, file_record, f"contract parse failed: {str(exc)}")
            raise HTTPException(status_code=500, detail=f"contract parse failed: {str(exc)}") from exc

        parsed_at = datetime.utcnow()
        text_preview = safe_text_preview(extracted_text, max_chars=request.max_preview_chars)

        contract_ext = load_json_text(contract.ext_json)
        file_record_ext = load_json_text(file_record.ext_json)

        contract_ext = merge_dict(
            contract_ext,
            {
                "parsing_result": {
                    "record_type": "contract",
                    "record_id": contract.id,
                    "file_record_id": file_record.id,
                    "parsed_at": parsed_at.isoformat(),
                    "extracted_text_length": len(extracted_text),
                    "extracted_page_count": extracted_page_count,
                    "text_preview": text_preview,
                    "validation_warnings": warnings,
                    "reserved_extracted_fields": {
                        "contract_code": contract.contract_code,
                        "contract_name": contract.contract_name,
                        "project_code": contract.project_code,
                        "customer_name": contract.customer_name,
                        "contract_amount": str(contract.contract_amount) if contract.contract_amount is not None else None,
                        "sign_date": str(contract.sign_date) if contract.sign_date else None,
                    },
                }
            },
        )

        file_record_ext = merge_dict(
            file_record_ext,
            {
                "parsing_result": {
                    "record_type": "contract_pdf",
                    "record_id": contract.id,
                    "parsed_at": parsed_at.isoformat(),
                    "extracted_text_length": len(extracted_text),
                    "extracted_page_count": extracted_page_count,
                    "text_preview": text_preview,
                    "validation_warnings": warnings,
                }
            },
        )

        contract.ext_json = dump_json_text(contract_ext)
        file_record.ext_json = dump_json_text(file_record_ext)

        contract.parse_status = ParseStatus.SUCCESS.value
        file_record.parse_status = ParseStatus.SUCCESS.value
        contract.next_step = NextStep.PRODUCT_SPLIT.value

        self.db.commit()
        self.db.refresh(contract)
        self.db.refresh(file_record)

        return self.get_contract_parse_result(contract_id)

    def get_contract(self, contract_id: int) -> ContractInfo:
        record = self.db.query(ContractInfo).filter(ContractInfo.id == contract_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="contract not found")
        return record

    def get_contract_parse_result(self, contract_id: int) -> Dict[str, Any]:
        contract = self.get_contract(contract_id)

        if not contract.file_record_id:
            raise HTTPException(status_code=400, detail="contract has no linked file_record_id")

        file_record = self.get_file_record(contract.file_record_id)

        contract_ext = load_json_text(contract.ext_json)
        parsing_result = contract_ext.get("parsing_result", {})
        validation_warnings = parsing_result.get("validation_warnings", [])

        parsed_at = parsing_result.get("parsed_at")
        parsed_at_value = None
        if parsed_at:
            try:
                parsed_at_value = datetime.fromisoformat(parsed_at)
            except Exception:
                parsed_at_value = None

        ext_fields = parsing_result.get("reserved_extracted_fields", {})
        if not isinstance(ext_fields, dict):
            ext_fields = {}

        # 当前生效值以 contract_info 为准，保证人工修正后列表页和详情页一致
        ext_fields = {
            **ext_fields,
            "contract_code": contract.contract_code,
            "contract_name": contract.contract_name,
            "project_code": contract.project_code,
            "customer_name": contract.customer_name,
            "contract_amount": str(contract.contract_amount) if contract.contract_amount is not None else None,
            "sign_date": str(contract.sign_date) if contract.sign_date else None,
        }

        return {
            "record_type": "contract",
            "record_id": contract.id,
            "file_record_id": file_record.id,
            "parse_status": contract.parse_status,
            "file_parse_status": file_record.parse_status,
            "file_name": file_record.file_name,
            "storage_path": file_record.storage_path,
            "extracted_text_length": parsing_result.get("extracted_text_length", 0),
            "extracted_page_count": parsing_result.get("extracted_page_count", 0),
            "text_preview": parsing_result.get("text_preview", ""),
            "warnings": validation_warnings if isinstance(validation_warnings, list) else [],
            "parsed_at": parsed_at_value,
            "ext": ext_fields,
        }

    def build_contract_internal_payload(self, contract_id: int) -> Dict[str, Any]:
        contract = self.get_contract(contract_id)
        result = self.get_contract_parse_result(contract_id)

        return {
            "record_type": "contract",
            "record_id": contract.id,
            "business_key": contract.contract_code,
            "status": contract.parse_status,
            "next_step": contract.next_step,
            "payload": {
                "contract_code": contract.contract_code,
                "contract_name": contract.contract_name,
                "project_code": contract.project_code,
                "customer_name": contract.customer_name,
                "contract_amount": str(contract.contract_amount) if contract.contract_amount is not None else None,
                "tax_included": contract.tax_included,
                "sign_date": str(contract.sign_date) if contract.sign_date else None,
                "file_record_id": contract.file_record_id,
                "parse_status": contract.parse_status,
                "text_preview": result["text_preview"],
                "extracted_text_length": result["extracted_text_length"],
                "extracted_page_count": result["extracted_page_count"],
                "reserved_extracted_fields": result["ext"],
            },
            "warnings": result["warnings"],
            "trace": {
                "module": "contract_parsing",
                "reserved_for": ["product_split"],
            },
        }

    def adjust_contract_parse_result(
        self,
        contract_id: int,
        request: ContractParseAdjustRequest,
    ) -> Dict[str, Any]:
        """
        人工修正合同解析结果：
        1. 更新 contract_info 当前生效字段
        2. 写入 contract_parse_adjust_log 留痕
        3. 更新 ext_json 中 parsing_result.reserved_extracted_fields
        4. 标记 manual_adjusted_flag / last_adjusted_at
        """
        contract = self.get_contract(contract_id)

        current_data = {
            "contract_code": contract.contract_code,
            "contract_name": contract.contract_name,
            "project_code": contract.project_code,
            "customer_name": contract.customer_name,
            "contract_amount": contract.contract_amount,
            "sign_date": contract.sign_date,
        }

        request_data = request.model_dump(exclude_unset=True)

        adjust_reason = request_data.pop("adjust_reason", None)
        adjusted_by = request_data.pop("adjusted_by", None)
        remarks = request_data.pop("remarks", None)

        changed_fields: List[Dict[str, Any]] = []

        for field_name in ALLOWED_ADJUST_FIELDS:
            if field_name not in request_data:
                continue

            old_value = current_data.get(field_name)
            new_value = request_data.get(field_name)

            old_norm = _normalize_adjust_value(old_value)
            new_norm = _normalize_adjust_value(new_value)

            if old_norm == new_norm:
                continue

            changed_fields.append(
                {
                    "field_name": field_name,
                    "old_value": old_norm,
                    "new_value": new_norm,
                    "raw_new_value": new_value,
                }
            )

        if not changed_fields:
            return {
                "contract_id": contract_id,
                "message": "no fields changed",
                "changed_fields": [],
            }

        now = datetime.utcnow()
        now_str = now.isoformat()

        # 1. 更新 ORM 对象中的标准字段
        for item in changed_fields:
            setattr(contract, item["field_name"], item["raw_new_value"])

        # 2. 更新 ext_json 中的 reserved_extracted_fields，保证查询结果同步
        contract_ext = load_json_text(contract.ext_json)
        parsing_result = contract_ext.get("parsing_result", {})
        reserved_fields = parsing_result.get("reserved_extracted_fields", {})
        if not isinstance(reserved_fields, dict):
            reserved_fields = {}

        for item in changed_fields:
            reserved_fields[item["field_name"]] = item["new_value"]

        parsing_result["reserved_extracted_fields"] = reserved_fields
        contract_ext["parsing_result"] = parsing_result
        contract.ext_json = dump_json_text(contract_ext)

        # 3. 使用 SQL 直接更新扩展字段，避免 ORM Model 未定义这些列时启动失败
        self.db.execute(
            text(
                """
                UPDATE contract_info
                SET manual_adjusted_flag = :manual_adjusted_flag,
                    last_adjusted_at = :last_adjusted_at
                WHERE id = :contract_id
                """
            ),
            {
                "manual_adjusted_flag": 1,
                "last_adjusted_at": now_str,
                "contract_id": contract_id,
            },
        )

        # 4. 记录每个字段的调整日志
        for item in changed_fields:
            self.db.execute(
                text(
                    """
                    INSERT INTO contract_parse_adjust_log
                    (
                        contract_id,
                        field_name,
                        old_value,
                        new_value,
                        adjust_reason,
                        source_type,
                        adjusted_by,
                        adjusted_at,
                        remarks
                    )
                    VALUES
                    (
                        :contract_id,
                        :field_name,
                        :old_value,
                        :new_value,
                        :adjust_reason,
                        :source_type,
                        :adjusted_by,
                        :adjusted_at,
                        :remarks
                    )
                    """
                ),
                {
                    "contract_id": contract_id,
                    "field_name": item["field_name"],
                    "old_value": item["old_value"],
                    "new_value": item["new_value"],
                    "adjust_reason": adjust_reason,
                    "source_type": "MANUAL",
                    "adjusted_by": adjusted_by,
                    "adjusted_at": now_str,
                    "remarks": remarks,
                },
            )

        self.db.commit()
        self.db.refresh(contract)

        return {
            "contract_id": contract_id,
            "message": "contract parse result adjusted successfully",
            "changed_fields": [
                {
                    "field_name": item["field_name"],
                    "old_value": item["old_value"],
                    "new_value": item["new_value"],
                }
                for item in changed_fields
            ],
            "manual_adjusted_flag": 1,
            "last_adjusted_at": now_str,
        }

    def list_contract_adjust_logs(self, contract_id: int) -> List[Dict[str, Any]]:
        contract = self.get_contract(contract_id)

        rows = self.db.execute(
            text(
                """
                SELECT
                    id,
                    contract_id,
                    field_name,
                    old_value,
                    new_value,
                    adjust_reason,
                    source_type,
                    adjusted_by,
                    adjusted_at,
                    remarks
                FROM contract_parse_adjust_log
                WHERE contract_id = :contract_id
                ORDER BY adjusted_at DESC, id DESC
                """
            ),
            {"contract_id": contract.id},
        ).mappings().all()

        results: List[Dict[str, Any]] = []
        for row in rows:
            adjusted_at = row["adjusted_at"]
            adjusted_at_value = None
            if adjusted_at:
                try:
                    adjusted_at_value = datetime.fromisoformat(str(adjusted_at))
                except Exception:
                    adjusted_at_value = None

            results.append(
                {
                    "id": row["id"],
                    "contract_id": row["contract_id"],
                    "field_name": row["field_name"],
                    "old_value": row["old_value"],
                    "new_value": row["new_value"],
                    "adjust_reason": row["adjust_reason"],
                    "source_type": row["source_type"],
                    "adjusted_by": row["adjusted_by"],
                    "adjusted_at": adjusted_at_value,
                    "remarks": row["remarks"],
                }
            )

        return results

    # ============================================================
    # Billing Record
    # ============================================================
    def parse_billing_record(self, billing_id: int, request: ParseRequest) -> Dict[str, Any]:
        billing_record = self.get_billing_record(billing_id)

        if not billing_record.file_record_id:
            raise HTTPException(status_code=400, detail="billing record has no linked file_record_id")

        file_record = self.get_file_record(billing_record.file_record_id)

        existing_result = self.get_billing_parse_result(billing_id)
        if not request.force_reparse and existing_result["parse_status"] == ParseStatus.SUCCESS.value:
            return existing_result

        try:
            extracted_text, extracted_page_count, warnings = extract_text_from_pdf(
                file_path=file_record.storage_path,
                max_pages=request.max_pages,
            )
        except FileNotFoundError as exc:
            self._mark_billing_record_parse_failed(billing_record, file_record, str(exc))
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ModuleNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail="pypdf is not installed. Please install dependency first.",
            ) from exc
        except Exception as exc:
            self._mark_billing_record_parse_failed(
                billing_record,
                file_record,
                f"billing record parse failed: {str(exc)}",
            )
            raise HTTPException(status_code=500, detail=f"billing record parse failed: {str(exc)}") from exc

        parsed_at = datetime.utcnow()
        text_preview = safe_text_preview(extracted_text, max_chars=request.max_preview_chars)

        billing_record_ext = load_json_text(billing_record.ext_json)
        file_record_ext = load_json_text(file_record.ext_json)

        billing_record_ext = merge_dict(
            billing_record_ext,
            {
                "parsing_result": {
                    "record_type": "billing_record",
                    "record_id": billing_record.id,
                    "file_record_id": file_record.id,
                    "parsed_at": parsed_at.isoformat(),
                    "extracted_text_length": len(extracted_text),
                    "extracted_page_count": extracted_page_count,
                    "text_preview": text_preview,
                    "validation_warnings": warnings,
                    "reserved_extracted_fields": {
                        "billing_code": billing_record.billing_code,
                        "project_code": billing_record.project_code,
                        "contract_code": billing_record.contract_code,
                        "billing_amount": str(billing_record.billing_amount) if billing_record.billing_amount is not None else None,
                        "billing_ratio": str(billing_record.billing_ratio) if billing_record.billing_ratio is not None else None,
                        "phase_name": billing_record.phase_name,
                        "billing_date": str(billing_record.billing_date) if billing_record.billing_date else None,
                    },
                }
            },
        )

        file_record_ext = merge_dict(
            file_record_ext,
            {
                "billing_parsing_result": {
                    "record_type": "billing_pdf",
                    "record_id": billing_record.id,
                    "parsed_at": parsed_at.isoformat(),
                    "extracted_text_length": len(extracted_text),
                    "extracted_page_count": extracted_page_count,
                    "text_preview": text_preview,
                    "validation_warnings": warnings,
                }
            },
        )

        billing_record.ext_json = dump_json_text(billing_record_ext)
        file_record.ext_json = dump_json_text(file_record_ext)
        file_record.parse_status = ParseStatus.SUCCESS.value

        self.db.commit()
        self.db.refresh(billing_record)
        self.db.refresh(file_record)

        return self.get_billing_parse_result(billing_id)

    def get_billing_record(self, billing_id: int) -> BillingRecord:
        record = self.db.query(BillingRecord).filter(BillingRecord.id == billing_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="billing record not found")
        return record

    def get_billing_parse_result(self, billing_id: int) -> Dict[str, Any]:
        billing_record = self.get_billing_record(billing_id)

        if not billing_record.file_record_id:
            raise HTTPException(status_code=400, detail="billing record has no linked file_record_id")

        file_record = self.get_file_record(billing_record.file_record_id)

        billing_record_ext = load_json_text(billing_record.ext_json)
        parsing_result = billing_record_ext.get("parsing_result", {})
        validation_warnings = parsing_result.get("validation_warnings", [])

        parse_status = ParseStatus.SUCCESS.value if parsing_result else ParseStatus.PENDING.value

        parsed_at = parsing_result.get("parsed_at")
        parsed_at_value = None
        if parsed_at:
            try:
                parsed_at_value = datetime.fromisoformat(parsed_at)
            except Exception:
                parsed_at_value = None

        return {
            "record_type": "billing_record",
            "record_id": billing_record.id,
            "file_record_id": file_record.id,
            "parse_status": parse_status,
            "file_parse_status": file_record.parse_status,
            "file_name": file_record.file_name,
            "storage_path": file_record.storage_path,
            "extracted_text_length": parsing_result.get("extracted_text_length", 0),
            "extracted_page_count": parsing_result.get("extracted_page_count", 0),
            "text_preview": parsing_result.get("text_preview", ""),
            "warnings": validation_warnings if isinstance(validation_warnings, list) else [],
            "parsed_at": parsed_at_value,
            "ext": parsing_result.get("reserved_extracted_fields", {}),
        }

    def build_billing_record_internal_payload(self, billing_id: int) -> Dict[str, Any]:
        billing_record = self.get_billing_record(billing_id)
        result = self.get_billing_parse_result(billing_id)

        return {
            "record_type": "billing_record",
            "record_id": billing_record.id,
            "business_key": billing_record.billing_code,
            "status": result["parse_status"],
            "next_step": billing_record.next_step,
            "payload": {
                "billing_code": billing_record.billing_code,
                "project_code": billing_record.project_code,
                "contract_code": billing_record.contract_code,
                "billing_date": str(billing_record.billing_date) if billing_record.billing_date else None,
                "billing_amount": str(billing_record.billing_amount) if billing_record.billing_amount is not None else None,
                "billing_ratio": str(billing_record.billing_ratio) if billing_record.billing_ratio is not None else None,
                "phase_name": billing_record.phase_name,
                "tax_included": billing_record.tax_included,
                "file_record_id": billing_record.file_record_id,
                "parse_status": result["parse_status"],
                "text_preview": result["text_preview"],
                "extracted_text_length": result["extracted_text_length"],
                "extracted_page_count": result["extracted_page_count"],
                "reserved_extracted_fields": result["ext"],
            },
            "warnings": result["warnings"],
            "trace": {
                "module": "contract_parsing",
                "reserved_for": ["phase_income_calc"],
            },
        }

    # ============================================================
    # File Record
    # ============================================================
    def get_file_record(self, file_id: int) -> FileRecord:
        record = self.db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="file record not found")
        return record

    # ============================================================
    # Internal Helpers
    # ============================================================
    def _mark_contract_parse_failed(
        self,
        contract: ContractInfo,
        file_record: FileRecord,
        reason: str,
    ) -> None:
        contract_ext = load_json_text(contract.ext_json)
        file_record_ext = load_json_text(file_record.ext_json)

        contract_ext = merge_dict(
            contract_ext,
            {
                "parsing_error": {
                    "reason": reason,
                    "at": datetime.utcnow().isoformat(),
                }
            },
        )

        file_record_ext = merge_dict(
            file_record_ext,
            {
                "parsing_error": {
                    "reason": reason,
                    "at": datetime.utcnow().isoformat(),
                }
            },
        )

        contract.ext_json = dump_json_text(contract_ext)
        file_record.ext_json = dump_json_text(file_record_ext)
        contract.parse_status = ParseStatus.FAILED.value
        file_record.parse_status = ParseStatus.FAILED.value

        self.db.commit()

    def _mark_billing_record_parse_failed(
        self,
        billing_record: BillingRecord,
        file_record: FileRecord,
        reason: str,
    ) -> None:
        billing_record_ext = load_json_text(billing_record.ext_json)
        file_record_ext = load_json_text(file_record.ext_json)

        billing_record_ext = merge_dict(
            billing_record_ext,
            {
                "parsing_error": {
                    "reason": reason,
                    "at": datetime.utcnow().isoformat(),
                }
            },
        )

        file_record_ext = merge_dict(
            file_record_ext,
            {
                "parsing_error": {
                    "reason": reason,
                    "at": datetime.utcnow().isoformat(),
                }
            },
        )

        billing_record.ext_json = dump_json_text(billing_record_ext)
        file_record.ext_json = dump_json_text(file_record_ext)
        file_record.parse_status = ParseStatus.FAILED.value

        self.db.commit()