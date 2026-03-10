import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.common.enums import FileType, NextStep, ParseStatus, RecordStatus, RuleStatus
from app.core.config import BILLING_UPLOAD_DIR, CONTRACT_UPLOAD_DIR
from app.models.billing_record import BillingRecord
from app.models.contract_info import ContractInfo
from app.models.file_record import FileRecord
from app.models.project_info import ProjectInfo
from app.modules.data_input.schemas import (
    BillingRecordCreateRequest,
    ContractCreateRequest,
    ProjectCreateRequest,
)
from app.modules.data_input.utils import (
    build_saved_filename,
    calculate_sha256,
    ensure_parent_dir,
    validate_pdf_file,
)


class DataInputService:
    """
    Data input module service.

    Current MVP responsibilities:
    - upload and register PDF files
    - create structured project / contract / billing records
    - perform minimum validation
    - reserve placeholder rule / workflow fields
    - provide downstream module payloads
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # File Upload
    # ============================================================
    async def upload_pdf(
        self,
        file: UploadFile,
        file_type: FileType,
        uploader: Optional[str] = None,
    ) -> FileRecord:
        try:
            validate_pdf_file(file)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="uploaded file is empty")

        file_hash = calculate_sha256(content)
        saved_name = build_saved_filename(file.filename or "unknown.pdf")

        save_dir = CONTRACT_UPLOAD_DIR if file_type == FileType.CONTRACT_PDF else BILLING_UPLOAD_DIR
        save_path = save_dir / saved_name
        ensure_parent_dir(save_path)

        with open(save_path, "wb") as f:
            f.write(content)

        record = FileRecord(
            file_uuid=uuid4().hex,
            file_name=file.filename or saved_name,
            file_type=file_type.value,
            storage_path=str(save_path),
            file_size=len(content),
            file_hash=file_hash,
            mime_type=file.content_type,
            uploader=uploader,
            parse_status=ParseStatus.PENDING.value,
            ext_json=json.dumps(
                {
                    "original_saved_name": saved_name,
                    "reserved_for_parser": True,
                },
                ensure_ascii=False,
            ),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    # ============================================================
    # Project
    # ============================================================
    def create_project(self, request: ProjectCreateRequest) -> ProjectInfo:
        exists = (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.project_code == request.project_code)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="project_code already exists")

        warnings = self._build_project_warnings(request)

        record = ProjectInfo(
            project_code=request.project_code,
            project_name=request.project_name,
            customer_name=request.customer_name,
            total_amount=request.total_amount,
            currency=request.currency,
            source_type=request.source_type.value,
            status=RecordStatus.VALIDATED.value,
            rule_status=RuleStatus.PLACEHOLDER_MATCHED.value,
            rule_template_code=None,
            next_step=NextStep.CONTRACT_PARSE.value,
            remarks=request.remarks,
            ext_json=json.dumps(
                {
                    "source_system": request.source_system,
                    "operator": request.operator,
                    "validation_warnings": warnings,
                    "reserved_rule_context": {
                        "rule_candidate_count": 0,
                        "rule_engine_ready": False,
                    },
                },
                ensure_ascii=False,
            ),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_project(self, project_id: int) -> ProjectInfo:
        record = self.db.query(ProjectInfo).filter(ProjectInfo.id == project_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="project not found")
        return record

    def list_projects(self) -> List[ProjectInfo]:
        return self.db.query(ProjectInfo).order_by(ProjectInfo.id.desc()).all()

    # ============================================================
    # Contract
    # ============================================================
    def create_contract(self, request: ContractCreateRequest) -> ContractInfo:
        exists = (
            self.db.query(ContractInfo)
            .filter(ContractInfo.contract_code == request.contract_code)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="contract_code already exists")

        project = (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.project_code == request.project_code)
            .first()
        )

        linked_file = None
        if request.file_record_id is not None:
            linked_file = (
                self.db.query(FileRecord)
                .filter(FileRecord.id == request.file_record_id)
                .first()
            )
            if not linked_file:
                raise HTTPException(status_code=400, detail="file_record_id does not exist")

        warnings = self._build_contract_warnings(
            project_exists=project is not None,
            file_exists=linked_file is not None if request.file_record_id else False,
        )

        status = RecordStatus.VALIDATED.value
        next_step = NextStep.PRODUCT_SPLIT.value
        if not project:
            status = RecordStatus.PENDING_REVIEW.value
            next_step = NextStep.MANUAL_REVIEW.value

        record = ContractInfo(
            contract_code=request.contract_code,
            contract_name=request.contract_name,
            project_code=request.project_code,
            customer_name=request.customer_name,
            contract_amount=request.contract_amount,
            tax_included=request.tax_included,
            sign_date=request.sign_date,
            file_record_id=request.file_record_id,
            parse_status=ParseStatus.PENDING.value,
            status=status,
            rule_status=RuleStatus.PLACEHOLDER_MATCHED.value,
            rule_template_code=None,
            next_step=next_step,
            remarks=request.remarks,
            ext_json=json.dumps(
                {
                    "source_system": request.source_system,
                    "operator": request.operator,
                    "validation_warnings": warnings,
                    "linked_project_exists": project is not None,
                    "linked_file_exists": linked_file is not None if request.file_record_id else False,
                    "reserved_for_contract_parsing": True,
                },
                ensure_ascii=False,
            ),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_contract(self, contract_id: int) -> ContractInfo:
        record = self.db.query(ContractInfo).filter(ContractInfo.id == contract_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="contract not found")
        return record

    def list_contracts(self) -> List[ContractInfo]:
        return self.db.query(ContractInfo).order_by(ContractInfo.id.desc()).all()

    # ============================================================
    # Billing Record
    # ============================================================
    def create_billing_record(self, request: BillingRecordCreateRequest) -> BillingRecord:
        exists = (
            self.db.query(BillingRecord)
            .filter(BillingRecord.billing_code == request.billing_code)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="billing_code already exists")

        project = (
            self.db.query(ProjectInfo)
            .filter(ProjectInfo.project_code == request.project_code)
            .first()
        )

        contract = None
        if request.contract_code:
            contract = (
                self.db.query(ContractInfo)
                .filter(ContractInfo.contract_code == request.contract_code)
                .first()
            )

        linked_file = None
        if request.file_record_id is not None:
            linked_file = (
                self.db.query(FileRecord)
                .filter(FileRecord.id == request.file_record_id)
                .first()
            )
            if not linked_file:
                raise HTTPException(status_code=400, detail="file_record_id does not exist")

        warnings = self._build_billing_warnings(
            project_exists=project is not None,
            contract_exists=contract is not None if request.contract_code else True,
            file_exists=linked_file is not None if request.file_record_id else False,
            billing_ratio=request.billing_ratio,
        )

        status = RecordStatus.READY_FOR_NEXT.value
        next_step = NextStep.PHASE_INCOME_CALC.value
        if not project:
            status = RecordStatus.PENDING_REVIEW.value
            next_step = NextStep.MANUAL_REVIEW.value

        record = BillingRecord(
            billing_code=request.billing_code,
            project_code=request.project_code,
            contract_code=request.contract_code,
            billing_date=request.billing_date,
            billing_amount=request.billing_amount,
            billing_ratio=request.billing_ratio,
            phase_name=request.phase_name,
            tax_included=request.tax_included,
            file_record_id=request.file_record_id,
            status=status,
            rule_status=RuleStatus.PLACEHOLDER_MATCHED.value,
            rule_template_code=None,
            next_step=next_step,
            remarks=request.remarks,
            ext_json=json.dumps(
                {
                    "source_system": request.source_system,
                    "operator": request.operator,
                    "validation_warnings": warnings,
                    "linked_project_exists": project is not None,
                    "linked_contract_exists": contract is not None if request.contract_code else None,
                    "linked_file_exists": linked_file is not None if request.file_record_id else False,
                    "reserved_for_phase_calc": True,
                },
                ensure_ascii=False,
            ),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_billing_record(self, billing_id: int) -> BillingRecord:
        record = self.db.query(BillingRecord).filter(BillingRecord.id == billing_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="billing record not found")
        return record

    def list_billing_records(self) -> List[BillingRecord]:
        return self.db.query(BillingRecord).order_by(BillingRecord.id.desc()).all()

    # ============================================================
    # File Query
    # ============================================================
    def get_file_record(self, file_id: int) -> FileRecord:
        record = self.db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="file record not found")
        return record

    def list_file_records(self) -> List[FileRecord]:
        return self.db.query(FileRecord).order_by(FileRecord.id.desc()).all()

    # ============================================================
    # Reserved Interface for Downstream Modules
    # ============================================================
    def build_project_internal_payload(self, project_id: int) -> Dict[str, Any]:
        record = self.get_project(project_id)
        warnings = self._extract_warnings(record.ext_json)
        return {
            "record_type": "project",
            "record_id": record.id,
            "business_key": record.project_code,
            "status": record.status,
            "next_step": record.next_step,
            "payload": {
                "project_code": record.project_code,
                "project_name": record.project_name,
                "customer_name": record.customer_name,
                "total_amount": str(record.total_amount),
                "currency": record.currency,
                "source_type": record.source_type,
            },
            "warnings": warnings,
            "trace": {
                "module": "data_input",
                "reserved_for": ["contract_parsing", "product_split"],
            },
        }

    def build_contract_internal_payload(self, contract_id: int) -> Dict[str, Any]:
        record = self.get_contract(contract_id)
        warnings = self._extract_warnings(record.ext_json)
        return {
            "record_type": "contract",
            "record_id": record.id,
            "business_key": record.contract_code,
            "status": record.status,
            "next_step": record.next_step,
            "payload": {
                "contract_code": record.contract_code,
                "contract_name": record.contract_name,
                "project_code": record.project_code,
                "customer_name": record.customer_name,
                "contract_amount": str(record.contract_amount),
                "tax_included": record.tax_included,
                "sign_date": str(record.sign_date) if record.sign_date else None,
                "file_record_id": record.file_record_id,
                "parse_status": record.parse_status,
            },
            "warnings": warnings,
            "trace": {
                "module": "data_input",
                "reserved_for": ["contract_parsing", "product_split"],
            },
        }

    def build_billing_internal_payload(self, billing_id: int) -> Dict[str, Any]:
        record = self.get_billing_record(billing_id)
        warnings = self._extract_warnings(record.ext_json)
        return {
            "record_type": "billing_record",
            "record_id": record.id,
            "business_key": record.billing_code,
            "status": record.status,
            "next_step": record.next_step,
            "payload": {
                "billing_code": record.billing_code,
                "project_code": record.project_code,
                "contract_code": record.contract_code,
                "billing_date": str(record.billing_date),
                "billing_amount": str(record.billing_amount),
                "billing_ratio": str(record.billing_ratio) if record.billing_ratio is not None else None,
                "phase_name": record.phase_name,
                "tax_included": record.tax_included,
                "file_record_id": record.file_record_id,
            },
            "warnings": warnings,
            "trace": {
                "module": "data_input",
                "reserved_for": ["phase_income_calc", "result_storage"],
            },
        }

    # ============================================================
    # Internal Helpers
    # ============================================================
    def _build_project_warnings(self, request: ProjectCreateRequest) -> List[str]:
        warnings: List[str] = []

        if request.currency != "CNY":
            warnings.append("current MVP mainly assumes CNY settlement")

        return warnings

    def _build_contract_warnings(
        self,
        project_exists: bool,
        file_exists: bool,
    ) -> List[str]:
        warnings: List[str] = []

        if not project_exists:
            warnings.append("linked project does not exist yet")

        if not file_exists:
            warnings.append("file_record_id is empty or linked file does not exist")

        return warnings

    def _build_billing_warnings(
        self,
        project_exists: bool,
        contract_exists: bool,
        file_exists: bool,
        billing_ratio: Optional[Any],
    ) -> List[str]:
        warnings: List[str] = []

        if not project_exists:
            warnings.append("linked project does not exist yet")

        if not contract_exists:
            warnings.append("linked contract does not exist yet")

        if not file_exists:
            warnings.append("file_record_id is empty or linked file does not exist")

        if billing_ratio is None:
            warnings.append("billing_ratio is empty, later amount-based logic may be needed")

        return warnings

    def _extract_warnings(self, ext_json: Optional[str]) -> List[str]:
        if not ext_json:
            return []

        try:
            parsed = json.loads(ext_json)
            warnings = parsed.get("validation_warnings", [])
            if isinstance(warnings, list):
                return warnings
            return []
        except Exception:
            return []