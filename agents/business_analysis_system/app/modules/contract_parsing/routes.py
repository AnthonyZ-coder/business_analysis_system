from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import APIResponse
from app.core.database import get_db
from app.modules.contract_parsing.schemas import (
    ContractParseAdjustRequest,
    ParseRequest,
)
from app.modules.contract_parsing.service import ContractParsingService

router = APIRouter(prefix="/api/v1/parsing", tags=["Contract Parsing"])


# ============================================================
# Contract APIs
# ============================================================
@router.post("/contracts/{contract_id}/parse", response_model=APIResponse)
def parse_contract(
    contract_id: int,
    request: ParseRequest,
    db: Session = Depends(get_db),
):
    service = ContractParsingService(db)
    record = service.parse_contract(contract_id, request)
    return APIResponse(data=record)


@router.get("/contracts/{contract_id}/result", response_model=APIResponse)
def get_contract_parse_result(
    contract_id: int,
    db: Session = Depends(get_db),
):
    service = ContractParsingService(db)
    record = service.get_contract_parse_result(contract_id)
    return APIResponse(data=record)


@router.put("/contracts/{contract_id}/adjust", response_model=APIResponse)
def adjust_contract_parse_result(
    contract_id: int,
    request: ContractParseAdjustRequest,
    db: Session = Depends(get_db),
):
    service = ContractParsingService(db)
    record = service.adjust_contract_parse_result(contract_id, request)
    return APIResponse(data=record)


@router.get("/contracts/{contract_id}/adjust-logs", response_model=APIResponse)
def list_contract_adjust_logs(
    contract_id: int,
    db: Session = Depends(get_db),
):
    service = ContractParsingService(db)
    records = service.list_contract_adjust_logs(contract_id)
    return APIResponse(data=records)


@router.get("/internal/contracts/{contract_id}/payload", response_model=APIResponse)
def get_contract_internal_payload(
    contract_id: int,
    db: Session = Depends(get_db),
):
    service = ContractParsingService(db)
    payload = service.build_contract_internal_payload(contract_id)
    return APIResponse(data=payload)


# ============================================================
# Billing Record APIs
# ============================================================
@router.post("/billing-records/{billing_id}/parse", response_model=APIResponse)
def parse_billing_record(
    billing_id: int,
    request: ParseRequest,
    db: Session = Depends(get_db),
):
    service = ContractParsingService(db)
    record = service.parse_billing_record(billing_id, request)
    return APIResponse(data=record)


@router.get("/billing-records/{billing_id}/result", response_model=APIResponse)
def get_billing_parse_result(
    billing_id: int,
    db: Session = Depends(get_db),
):
    service = ContractParsingService(db)
    record = service.get_billing_parse_result(billing_id)
    return APIResponse(data=record)


@router.get("/internal/billing-records/{billing_id}/payload", response_model=APIResponse)
def get_billing_internal_payload(
    billing_id: int,
    db: Session = Depends(get_db),
):
    service = ContractParsingService(db)
    payload = service.build_billing_record_internal_payload(billing_id)
    return APIResponse(data=payload)