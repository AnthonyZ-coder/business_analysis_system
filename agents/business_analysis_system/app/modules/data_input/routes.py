from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.common.enums import FileType
from app.common.response import APIResponse
from app.core.database import get_db
from app.modules.data_input.schemas import (
    BillingRecordCreateRequest,
    ContractCreateRequest,
    ProjectCreateRequest,
)
from app.modules.data_input.service import DataInputService

router = APIRouter(prefix="/api/v1/input", tags=["Data Input"])


# ============================================================
# File Upload APIs
# ============================================================
@router.post("/upload/contract", response_model=APIResponse)
async def upload_contract_pdf(
    file: UploadFile = File(...),
    uploader: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = await service.upload_pdf(
        file=file,
        file_type=FileType.CONTRACT_PDF,
        uploader=uploader,
    )
    return APIResponse(
        data={
            "id": record.id,
            "file_uuid": record.file_uuid,
            "file_name": record.file_name,
            "file_type": record.file_type,
            "storage_path": record.storage_path,
            "file_size": record.file_size,
            "file_hash": record.file_hash,
            "mime_type": record.mime_type,
            "upload_time": record.upload_time,
            "uploader": record.uploader,
            "parse_status": record.parse_status,
        }
    )


@router.post("/upload/billing", response_model=APIResponse)
async def upload_billing_pdf(
    file: UploadFile = File(...),
    uploader: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = await service.upload_pdf(
        file=file,
        file_type=FileType.BILLING_PDF,
        uploader=uploader,
    )
    return APIResponse(
        data={
            "id": record.id,
            "file_uuid": record.file_uuid,
            "file_name": record.file_name,
            "file_type": record.file_type,
            "storage_path": record.storage_path,
            "file_size": record.file_size,
            "file_hash": record.file_hash,
            "mime_type": record.mime_type,
            "upload_time": record.upload_time,
            "uploader": record.uploader,
            "parse_status": record.parse_status,
        }
    )


# ============================================================
# Project APIs
# ============================================================
@router.post("/projects", response_model=APIResponse)
def create_project(
    request: ProjectCreateRequest,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = service.create_project(request)
    return APIResponse(
        data={
            "id": record.id,
            "project_code": record.project_code,
            "project_name": record.project_name,
            "customer_name": record.customer_name,
            "total_amount": str(record.total_amount),
            "currency": record.currency,
            "source_type": record.source_type,
            "status": record.status,
            "rule_status": record.rule_status,
            "rule_template_code": record.rule_template_code,
            "next_step": record.next_step,
            "remarks": record.remarks,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
    )


@router.get("/projects/{project_id}", response_model=APIResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = service.get_project(project_id)
    return APIResponse(
        data={
            "id": record.id,
            "project_code": record.project_code,
            "project_name": record.project_name,
            "customer_name": record.customer_name,
            "total_amount": str(record.total_amount),
            "currency": record.currency,
            "source_type": record.source_type,
            "status": record.status,
            "rule_status": record.rule_status,
            "rule_template_code": record.rule_template_code,
            "next_step": record.next_step,
            "remarks": record.remarks,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
    )


@router.get("/projects", response_model=APIResponse)
def list_projects(
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    records = service.list_projects()

    data: List[Dict[str, Any]] = []
    for record in records:
        data.append(
            {
                "id": record.id,
                "project_code": record.project_code,
                "project_name": record.project_name,
                "customer_name": record.customer_name,
                "total_amount": str(record.total_amount),
                "currency": record.currency,
                "source_type": record.source_type,
                "status": record.status,
                "rule_status": record.rule_status,
                "rule_template_code": record.rule_template_code,
                "next_step": record.next_step,
                "remarks": record.remarks,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
        )
    return APIResponse(data=data)


# ============================================================
# Contract APIs
# ============================================================
@router.post("/contracts", response_model=APIResponse)
def create_contract(
    request: ContractCreateRequest,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = service.create_contract(request)
    return APIResponse(
        data={
            "id": record.id,
            "contract_code": record.contract_code,
            "contract_name": record.contract_name,
            "project_code": record.project_code,
            "customer_name": record.customer_name,
            "contract_amount": str(record.contract_amount),
            "tax_included": record.tax_included,
            "sign_date": record.sign_date,
            "file_record_id": record.file_record_id,
            "parse_status": record.parse_status,
            "status": record.status,
            "rule_status": record.rule_status,
            "rule_template_code": record.rule_template_code,
            "next_step": record.next_step,
            "remarks": record.remarks,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
    )


@router.get("/contracts/{contract_id}", response_model=APIResponse)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = service.get_contract(contract_id)
    return APIResponse(
        data={
            "id": record.id,
            "contract_code": record.contract_code,
            "contract_name": record.contract_name,
            "project_code": record.project_code,
            "customer_name": record.customer_name,
            "contract_amount": str(record.contract_amount),
            "tax_included": record.tax_included,
            "sign_date": record.sign_date,
            "file_record_id": record.file_record_id,
            "parse_status": record.parse_status,
            "status": record.status,
            "rule_status": record.rule_status,
            "rule_template_code": record.rule_template_code,
            "next_step": record.next_step,
            "remarks": record.remarks,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
    )


@router.get("/contracts", response_model=APIResponse)
def list_contracts(
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    records = service.list_contracts()

    data: List[Dict[str, Any]] = []
    for record in records:
        data.append(
            {
                "id": record.id,
                "contract_code": record.contract_code,
                "contract_name": record.contract_name,
                "project_code": record.project_code,
                "customer_name": record.customer_name,
                "contract_amount": str(record.contract_amount),
                "tax_included": record.tax_included,
                "sign_date": record.sign_date,
                "file_record_id": record.file_record_id,
                "parse_status": record.parse_status,
                "status": record.status,
                "rule_status": record.rule_status,
                "rule_template_code": record.rule_template_code,
                "next_step": record.next_step,
                "remarks": record.remarks,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
        )
    return APIResponse(data=data)


# ============================================================
# Billing Record APIs
# ============================================================
@router.post("/billing-records", response_model=APIResponse)
def create_billing_record(
    request: BillingRecordCreateRequest,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = service.create_billing_record(request)
    return APIResponse(
        data={
            "id": record.id,
            "billing_code": record.billing_code,
            "project_code": record.project_code,
            "contract_code": record.contract_code,
            "billing_date": record.billing_date,
            "billing_amount": str(record.billing_amount),
            "billing_ratio": str(record.billing_ratio) if record.billing_ratio is not None else None,
            "phase_name": record.phase_name,
            "tax_included": record.tax_included,
            "file_record_id": record.file_record_id,
            "status": record.status,
            "rule_status": record.rule_status,
            "rule_template_code": record.rule_template_code,
            "next_step": record.next_step,
            "remarks": record.remarks,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
    )


@router.get("/billing-records/{billing_id}", response_model=APIResponse)
def get_billing_record(
    billing_id: int,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = service.get_billing_record(billing_id)
    return APIResponse(
        data={
            "id": record.id,
            "billing_code": record.billing_code,
            "project_code": record.project_code,
            "contract_code": record.contract_code,
            "billing_date": record.billing_date,
            "billing_amount": str(record.billing_amount),
            "billing_ratio": str(record.billing_ratio) if record.billing_ratio is not None else None,
            "phase_name": record.phase_name,
            "tax_included": record.tax_included,
            "file_record_id": record.file_record_id,
            "status": record.status,
            "rule_status": record.rule_status,
            "rule_template_code": record.rule_template_code,
            "next_step": record.next_step,
            "remarks": record.remarks,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
    )


@router.get("/billing-records", response_model=APIResponse)
def list_billing_records(
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    records = service.list_billing_records()

    data: List[Dict[str, Any]] = []
    for record in records:
        data.append(
            {
                "id": record.id,
                "billing_code": record.billing_code,
                "project_code": record.project_code,
                "contract_code": record.contract_code,
                "billing_date": record.billing_date,
                "billing_amount": str(record.billing_amount),
                "billing_ratio": str(record.billing_ratio) if record.billing_ratio is not None else None,
                "phase_name": record.phase_name,
                "tax_included": record.tax_included,
                "file_record_id": record.file_record_id,
                "status": record.status,
                "rule_status": record.rule_status,
                "rule_template_code": record.rule_template_code,
                "next_step": record.next_step,
                "remarks": record.remarks,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
        )
    return APIResponse(data=data)


# ============================================================
# File Query APIs
# ============================================================
@router.get("/files/{file_id}", response_model=APIResponse)
def get_file_record(
    file_id: int,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    record = service.get_file_record(file_id)
    return APIResponse(
        data={
            "id": record.id,
            "file_uuid": record.file_uuid,
            "file_name": record.file_name,
            "file_type": record.file_type,
            "storage_path": record.storage_path,
            "file_size": record.file_size,
            "file_hash": record.file_hash,
            "mime_type": record.mime_type,
            "upload_time": record.upload_time,
            "uploader": record.uploader,
            "parse_status": record.parse_status,
        }
    )


@router.get("/files", response_model=APIResponse)
def list_file_records(
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    records = service.list_file_records()

    data: List[Dict[str, Any]] = []
    for record in records:
        data.append(
            {
                "id": record.id,
                "file_uuid": record.file_uuid,
                "file_name": record.file_name,
                "file_type": record.file_type,
                "storage_path": record.storage_path,
                "file_size": record.file_size,
                "file_hash": record.file_hash,
                "mime_type": record.mime_type,
                "upload_time": record.upload_time,
                "uploader": record.uploader,
                "parse_status": record.parse_status,
            }
        )
    return APIResponse(data=data)


# ============================================================
# Reserved APIs for Downstream Modules
# ============================================================
@router.get("/internal/projects/{project_id}/payload", response_model=APIResponse)
def get_project_internal_payload(
    project_id: int,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    payload = service.build_project_internal_payload(project_id)
    return APIResponse(data=payload)


@router.get("/internal/contracts/{contract_id}/payload", response_model=APIResponse)
def get_contract_internal_payload(
    contract_id: int,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    payload = service.build_contract_internal_payload(contract_id)
    return APIResponse(data=payload)


@router.get("/internal/billing-records/{billing_id}/payload", response_model=APIResponse)
def get_billing_internal_payload(
    billing_id: int,
    db: Session = Depends(get_db),
):
    service = DataInputService(db)
    payload = service.build_billing_internal_payload(billing_id)
    return APIResponse(data=payload)