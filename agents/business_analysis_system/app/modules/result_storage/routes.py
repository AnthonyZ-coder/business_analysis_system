from fastapi import APIRouter, Query

from app.common.response import APIResponse
from app.modules.result_storage.schemas import (
    ResultStorageCreateFromPhaseIncomeRequest,
    WorkflowStatusLogCreateRequest,
)
from app.modules.result_storage.service import ResultStorageService

router = APIRouter(prefix="/api/v1/result-storage", tags=["Result Storage"])


# ============================================================
# Result Record APIs
# ============================================================
@router.post("/records/from-phase-income/{phase_income_record_id}", response_model=APIResponse)
def create_result_from_phase_income(
    phase_income_record_id: int,
    request: ResultStorageCreateFromPhaseIncomeRequest,
):
    service = ResultStorageService()
    record = service.create_result_from_phase_income(phase_income_record_id, request)
    return APIResponse(data=record)


@router.get("/records/{result_id}", response_model=APIResponse)
def get_result_record(result_id: int):
    service = ResultStorageService()
    record = service.get_result_record(result_id)
    return APIResponse(data=record)


# ============================================================
# Workflow Status Log APIs
# ============================================================
@router.post("/workflow/logs", response_model=APIResponse)
def create_workflow_status_log(request: WorkflowStatusLogCreateRequest):
    service = ResultStorageService()
    record = service.create_workflow_status_log(request)
    return APIResponse(data=record)


@router.get("/workflow/logs", response_model=APIResponse)
def list_workflow_status_logs(
    business_key: str = Query(..., min_length=2, max_length=128),
    limit: int = Query(default=100, ge=1, le=500),
):
    service = ResultStorageService()
    records = service.list_workflow_status_logs(business_key=business_key, limit=limit)
    return APIResponse(data=records)


# ============================================================
# Internal Payload APIs
# ============================================================
@router.get("/internal/records/{result_id}/payload", response_model=APIResponse)
def get_result_internal_payload(result_id: int):
    service = ResultStorageService()
    payload = service.build_result_internal_payload(result_id)
    return APIResponse(data=payload)