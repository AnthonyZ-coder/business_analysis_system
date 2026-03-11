from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.common.enums import NextStep, ParseStatus
from app.models.billing_record import BillingRecord
from app.models.contract_info import ContractInfo
from app.models.file_record import FileRecord
from app.modules.contract_parsing.schemas import ParseRequest
from app.modules.contract_parsing.utils import (
    dump_json_text,
    extract_text_from_pdf,
    load_json_text,
    merge_dict,
    safe_text_preview,
)


class ContractParsingService:
    """
    Contract parsing module service.

    Current MVP responsibilities:
    - read contract / billing PDF files from file_record
    - extract raw text from PDF files
    - persist parsing result into ext_json
    - update parse statuses
    - provide downstream module payloads
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
                        "contract_amount": str(contract.contract_amount),
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
            "ext": parsing_result.get("reserved_extracted_fields", {}),
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
                "contract_amount": str(contract.contract_amount),
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
                        "billing_amount": str(billing_record.billing_amount),
                        "billing_ratio": str(billing_record.billing_ratio) if billing_record.billing_ratio is not None else None,
                        "phase_name": billing_record.phase_name,
                        "billing_date": str(billing_record.billing_date),
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
                "billing_date": str(billing_record.billing_date),
                "billing_amount": str(billing_record.billing_amount),
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