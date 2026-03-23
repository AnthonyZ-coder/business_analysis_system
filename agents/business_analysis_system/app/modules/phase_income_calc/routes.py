from fastapi import APIRouter, Query

from app.common.response import APIResponse
from app.modules.phase_income_calc.schemas import (
    PhaseIncomeCreateRequest,
    PhaseIncomeUpdateRequest,
)
from app.modules.phase_income_calc.service import PhaseIncomeCalcService

router = APIRouter(prefix="/api/v1/phase-income", tags=["Phase Income Calc"])


# ============================================================
# Search / Query APIs
# ============================================================
@router.get("/search/contracts", response_model=APIResponse)
def search_contracts(
    q: str = Query(..., min_length=1, description="合同名称 / 合同编码 / 项目编码 / 项目名称关键词"),
    limit: int = Query(default=20, ge=1, le=100),
):
    service = PhaseIncomeCalcService()
    records = service.search_contracts(keyword=q, limit=limit)
    return APIResponse(data=records)


@router.get("/rules", response_model=APIResponse)
def list_rules(
    limit: int = Query(default=100, ge=1, le=500),
):
    service = PhaseIncomeCalcService()
    records = service.list_rules(limit=limit)
    return APIResponse(data=records)


# ============================================================
# Phase Income Record APIs
# ============================================================
@router.post("/records", response_model=APIResponse)
def create_phase_income_record(request: PhaseIncomeCreateRequest):
    service = PhaseIncomeCalcService()
    record = service.create_phase_income_record(request)
    return APIResponse(data=record)


@router.get("/records/{record_id}", response_model=APIResponse)
def get_phase_income_record(record_id: int):
    service = PhaseIncomeCalcService()
    record = service.get_phase_income_record(record_id)
    return APIResponse(data=record)


@router.put("/records/{record_id}", response_model=APIResponse)
def update_phase_income_record(record_id: int, request: PhaseIncomeUpdateRequest):
    service = PhaseIncomeCalcService()
    record = service.update_phase_income_record(record_id, request)
    return APIResponse(data=record)


# ============================================================
# Internal Payload APIs
# ============================================================
@router.get("/internal/records/{record_id}/payload", response_model=APIResponse)
def get_phase_income_internal_payload(record_id: int):
    service = PhaseIncomeCalcService()
    payload = service.build_phase_income_internal_payload(record_id)
    return APIResponse(data=payload)