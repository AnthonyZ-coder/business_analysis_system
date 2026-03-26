from fastapi import APIRouter, Query

from app.common.response import APIResponse
from app.modules.query_display.schemas import (
    ProjectSummaryQueryRequest,
    ResultListQueryRequest,
    WorkflowQueryRequest,
)
from app.modules.query_display.service import QueryDisplayService

router = APIRouter(prefix="/api/v1/query-display", tags=["Query Display"])


# ============================================================
# Result List APIs
# ============================================================
@router.get("/results", response_model=APIResponse)
def list_results(
    billing_period: str | None = Query(default=None, min_length=7, max_length=16),
    project_code: str | None = Query(default=None, min_length=2, max_length=64),
    project_name: str | None = Query(default=None, min_length=1, max_length=255),
    contract_code: str | None = Query(default=None, min_length=1, max_length=64),
    contract_name: str | None = Query(default=None, min_length=1, max_length=255),
    rule_name: str | None = Query(default=None, min_length=1, max_length=255),
    result_status: str | None = Query(default=None, min_length=1, max_length=32),
    limit: int = Query(default=100, ge=1, le=500),
):
    service = QueryDisplayService()
    request = ResultListQueryRequest(
        billing_period=billing_period,
        project_code=project_code,
        project_name=project_name,
        contract_code=contract_code,
        contract_name=contract_name,
        rule_name=rule_name,
        result_status=result_status,
        limit=limit,
    )
    records = service.list_results(request)
    return APIResponse(data=records)


# ============================================================
# Result Detail APIs
# ============================================================
@router.get("/results/{result_id}", response_model=APIResponse)
def get_result_detail(result_id: int):
    service = QueryDisplayService()
    record = service.get_result_detail(result_id)
    return APIResponse(data=record)


# ============================================================
# Project Summary APIs
# ============================================================
@router.get("/project-summary", response_model=APIResponse)
def get_project_summary(
    billing_period: str | None = Query(default=None, min_length=7, max_length=16),
    project_code: str | None = Query(default=None, min_length=2, max_length=64),
    limit: int = Query(default=100, ge=1, le=500),
):
    service = QueryDisplayService()
    request = ProjectSummaryQueryRequest(
        billing_period=billing_period,
        project_code=project_code,
        limit=limit,
    )
    records = service.get_project_summary(request)
    return APIResponse(data=records)


# ============================================================
# Workflow Query APIs
# ============================================================
@router.get("/workflow", response_model=APIResponse)
def list_workflow_logs(
    business_key: str = Query(..., min_length=2, max_length=128),
    limit: int = Query(default=100, ge=1, le=500),
):
    service = QueryDisplayService()
    request = WorkflowQueryRequest(
        business_key=business_key,
        limit=limit,
    )
    records = service.list_workflow_logs(request)
    return APIResponse(data=records)


# ============================================================
# Internal Payload APIs
# ============================================================
@router.get("/internal/results/{result_id}/payload", response_model=APIResponse)
def get_result_query_payload(result_id: int):
    service = QueryDisplayService()
    payload = service.build_result_query_payload(result_id)
    return APIResponse(data=payload)