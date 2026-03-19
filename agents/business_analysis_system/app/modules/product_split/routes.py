from fastapi import APIRouter

from app.common.response import APIResponse
from app.modules.product_split.schemas import (
    ProductSplitDraftCreateRequest,
    ProductSplitDraftSubmitRequest,
    ProductSplitDraftUpdateRequest,
    ProductSplitSuggestionCreateRequest,
    ProjectSplitRuleBindingCreateRequest,
)
from app.modules.product_split.service import ProductSplitService

router = APIRouter(prefix="/api/v1/product-split", tags=["Product Split"])


# ============================================================
# Suggestion APIs
# ============================================================
@router.post("/suggestions", response_model=APIResponse)
def create_suggestion(request: ProductSplitSuggestionCreateRequest):
    service = ProductSplitService()
    record = service.create_suggestion(request)
    return APIResponse(data=record)


@router.get("/suggestions/{suggestion_id}", response_model=APIResponse)
def get_suggestion(suggestion_id: int):
    service = ProductSplitService()
    record = service.get_suggestion(suggestion_id)
    return APIResponse(data=record)


# ============================================================
# Draft APIs
# ============================================================
@router.post("/drafts", response_model=APIResponse)
def create_draft(request: ProductSplitDraftCreateRequest):
    service = ProductSplitService()
    record = service.create_draft(request)
    return APIResponse(data=record)


@router.get("/drafts/{draft_id}", response_model=APIResponse)
def get_draft(draft_id: int):
    service = ProductSplitService()
    record = service.get_draft(draft_id)
    return APIResponse(data=record)


@router.put("/drafts/{draft_id}", response_model=APIResponse)
def update_draft(draft_id: int, request: ProductSplitDraftUpdateRequest):
    service = ProductSplitService()
    record = service.update_draft(draft_id, request)
    return APIResponse(data=record)


@router.post("/drafts/{draft_id}/submit", response_model=APIResponse)
def submit_draft_to_rule(draft_id: int, request: ProductSplitDraftSubmitRequest):
    service = ProductSplitService()
    record = service.submit_draft_to_rule(draft_id, request)
    return APIResponse(data=record)


# ============================================================
# Rule APIs
# ============================================================
@router.get("/rules/{rule_id}", response_model=APIResponse)
def get_rule(rule_id: int):
    service = ProductSplitService()
    record = service.get_rule(rule_id)
    return APIResponse(data=record)


# ============================================================
# Project Binding APIs
# ============================================================
@router.post("/bindings", response_model=APIResponse)
def create_project_rule_binding(request: ProjectSplitRuleBindingCreateRequest):
    service = ProductSplitService()
    record = service.create_project_rule_binding(request)
    return APIResponse(data=record)


@router.get("/bindings/{binding_id}", response_model=APIResponse)
def get_project_rule_binding(binding_id: int):
    service = ProductSplitService()
    record = service.get_project_rule_binding(binding_id)
    return APIResponse(data=record)


# ============================================================
# Internal Payload APIs
# ============================================================
@router.get("/internal/rules/{rule_id}/payload", response_model=APIResponse)
def get_rule_internal_payload(rule_id: int):
    service = ProductSplitService()
    payload = service.build_rule_internal_payload(rule_id)
    return APIResponse(data=payload)