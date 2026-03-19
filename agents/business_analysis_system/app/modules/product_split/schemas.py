from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


# ============================================================
# Common Detail Models
# ============================================================
class ProductSplitDetailItem(BaseModel):
    product_code: str = Field(..., min_length=2, max_length=64)
    split_ratio: Decimal = Field(..., ge=0, le=1)
    adjust_reason: Optional[str] = None
    remarks: Optional[str] = None


class ProductSplitSuggestionDetailResponse(BaseModel):
    id: int
    suggestion_id: int
    product_code: str
    product_name: str
    category_code: str
    split_ratio: Decimal
    confidence_score: Optional[Decimal] = None
    source_type: str
    evidence_text: Optional[str] = None
    evidence_page_info: Optional[str] = None
    matrix_weight: Optional[Decimal] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    remarks: Optional[str] = None


class ProductSplitDraftDetailResponse(BaseModel):
    id: int
    draft_id: int
    product_code: str
    product_name: str
    category_code: str
    split_ratio: Decimal
    source_type: str
    based_suggestion_detail_id: Optional[int] = None
    adjust_reason: Optional[str] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    remarks: Optional[str] = None


class ProductSplitRuleDetailResponse(BaseModel):
    id: int
    rule_id: int
    product_code: str
    product_name: str
    category_code: str
    split_ratio: Decimal
    source_type: str
    based_draft_detail_id: Optional[int] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    remarks: Optional[str] = None


# ============================================================
# Suggestion Models
# ============================================================
class ProductSplitSuggestionCreateRequest(BaseModel):
    project_code: str = Field(..., min_length=2, max_length=64)
    contract_id: Optional[int] = None
    contract_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    suggestion_name: str = Field(..., min_length=2, max_length=255)
    source_type: str = Field(..., min_length=2, max_length=32)  # LLM / CASE_RAG / TEMPLATE
    source_model: Optional[str] = Field(default=None, max_length=128)
    llm_enabled_flag: int = Field(default=1, ge=0, le=1)
    category_split_json: Optional[Dict[str, Decimal]] = None
    evidence_summary: Optional[str] = None
    reference_case_ids: Optional[List[int]] = None
    matrix_applied_flag: int = Field(default=0, ge=0, le=1)
    created_by: Optional[str] = Field(default=None, max_length=64)
    remarks: Optional[str] = None
    details: List[ProductSplitDetailItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_details_total_ratio(self):
        if self.details:
            total = sum(item.split_ratio for item in self.details)
            if abs(total - Decimal("1")) > Decimal("0.0001"):
                raise ValueError("sum of details.split_ratio must be 1")
        return self


class ProductSplitSuggestionResponse(BaseModel):
    id: int
    suggestion_code: str
    project_code: str
    contract_id: Optional[int] = None
    contract_code: Optional[str] = None
    suggestion_name: str
    source_type: str
    source_model: Optional[str] = None
    llm_enabled_flag: int
    category_split_json: Optional[Dict[str, Any]] = None
    evidence_summary: Optional[str] = None
    reference_case_ids: Optional[str] = None
    matrix_applied_flag: int
    review_status: str
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    status: str
    version_no: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    remarks: Optional[str] = None
    details: List[ProductSplitSuggestionDetailResponse] = Field(default_factory=list)


# ============================================================
# Draft Models
# ============================================================
class ProductSplitDraftCreateRequest(BaseModel):
    project_code: str = Field(..., min_length=2, max_length=64)
    contract_id: Optional[int] = None
    contract_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    draft_name: str = Field(..., min_length=2, max_length=255)
    draft_source_type: str = Field(..., min_length=2, max_length=32)  # MANUAL / LLM / TEMPLATE / CASE_RAG
    llm_enabled_flag: int = Field(default=0, ge=0, le=1)
    from_suggestion_id: Optional[int] = None
    category_split_json: Optional[Dict[str, Decimal]] = None
    created_by: Optional[str] = Field(default=None, max_length=64)
    remarks: Optional[str] = None
    details: List[ProductSplitDetailItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_details_total_ratio(self):
        if not self.details:
            raise ValueError("details cannot be empty")

        total = sum(item.split_ratio for item in self.details)
        if abs(total - Decimal("1")) > Decimal("0.0001"):
            raise ValueError("sum of details.split_ratio must be 1")

        return self


class ProductSplitDraftUpdateRequest(BaseModel):
    draft_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    category_split_json: Optional[Dict[str, Decimal]] = None
    updated_by: Optional[str] = Field(default=None, max_length=64)
    remarks: Optional[str] = None
    details: Optional[List[ProductSplitDetailItem]] = None

    @model_validator(mode="after")
    def validate_details_total_ratio(self):
        if self.details is not None:
            if not self.details:
                raise ValueError("details cannot be empty when provided")

            total = sum(item.split_ratio for item in self.details)
            if abs(total - Decimal("1")) > Decimal("0.0001"):
                raise ValueError("sum of details.split_ratio must be 1")

        return self


class ProductSplitDraftResponse(BaseModel):
    id: int
    draft_code: str
    project_code: str
    contract_id: Optional[int] = None
    contract_code: Optional[str] = None
    draft_name: str
    draft_source_type: str
    llm_enabled_flag: int
    from_suggestion_id: Optional[int] = None
    category_split_json: Optional[Dict[str, Any]] = None
    edit_status: str
    review_status: str
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    status: str
    version_no: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    remarks: Optional[str] = None
    details: List[ProductSplitDraftDetailResponse] = Field(default_factory=list)


class ProductSplitDraftSubmitRequest(BaseModel):
    rule_name: str = Field(..., min_length=2, max_length=255)
    rule_type: str = Field(..., min_length=2, max_length=32)  # MANUAL / LLM_CONFIRMED / TEMPLATE / CASE_RAG
    project_type_tag: Optional[str] = Field(default=None, max_length=128)
    applicable_scope: Optional[str] = None
    reviewer: Optional[str] = Field(default=None, max_length=64)
    created_by: Optional[str] = Field(default=None, max_length=64)
    remarks: Optional[str] = None


# ============================================================
# Rule Models
# ============================================================
class ProductSplitRuleResponse(BaseModel):
    id: int
    rule_code: str
    rule_name: str
    rule_type: str
    project_type_tag: Optional[str] = None
    applicable_scope: Optional[str] = None
    category_split_json: Optional[Dict[str, Any]] = None
    source_draft_id: int
    review_status: str
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    is_default: int
    status: str
    version_no: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    remarks: Optional[str] = None
    details: List[ProductSplitRuleDetailResponse] = Field(default_factory=list)


# ============================================================
# Binding Models
# ============================================================
class ProjectSplitRuleBindingCreateRequest(BaseModel):
    project_code: str = Field(..., min_length=2, max_length=64)
    contract_id: Optional[int] = None
    contract_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    rule_id: int
    selected_by: Optional[str] = Field(default=None, max_length=64)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    remarks: Optional[str] = None

    @model_validator(mode="after")
    def validate_effective_range(self):
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError("effective_from cannot be later than effective_to")
        return self


class ProjectSplitRuleBindingResponse(BaseModel):
    id: int
    project_code: str
    contract_id: Optional[int] = None
    contract_code: Optional[str] = None
    rule_id: int
    binding_status: str
    selected_by: Optional[str] = None
    selected_at: datetime
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    remarks: Optional[str] = None


# ============================================================
# Internal Payload Models
# ============================================================
class InternalPayloadResponse(BaseModel):
    record_type: str
    record_id: int
    business_key: str
    status: str
    next_step: Optional[str] = None
    payload: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
    trace: Dict[str, Any] = Field(default_factory=dict)