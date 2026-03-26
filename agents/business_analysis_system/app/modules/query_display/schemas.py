from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Common Models
# ============================================================
class WorkflowLogItemResponse(BaseModel):
    id: int
    business_key: str
    business_type: str
    source_module: str
    from_status: Optional[str] = None
    to_status: str
    action_type: Optional[str] = None
    operator: Optional[str] = None
    action_time: datetime
    related_record_type: Optional[str] = None
    related_record_id: Optional[int] = None
    message: Optional[str] = None
    ext_json: Optional[Dict[str, Any]] = None


class ResultDetailItemResponse(BaseModel):
    id: int
    result_id: int
    product_code: str
    product_name: str
    category_code: str
    split_ratio: Decimal
    tax_included_amount: Decimal
    tax_excluded_amount: Decimal
    sort_order: int
    created_at: datetime
    updated_at: datetime
    remarks: Optional[str] = None


class ResultCategorySummaryItemResponse(BaseModel):
    category_code: str
    category_name: str
    split_ratio: Decimal
    tax_included_amount: Decimal
    tax_excluded_amount: Decimal


# ============================================================
# Result List Models
# ============================================================
class ResultListItemResponse(BaseModel):
    result_id: int
    result_code: str

    billing_period: str
    billing_date: Optional[date] = None

    project_code: str
    project_name: Optional[str] = None

    contract_id: Optional[int] = None
    contract_code: Optional[str] = None
    contract_name: Optional[str] = None

    rule_id: Optional[int] = None
    rule_code: Optional[str] = None
    rule_name: Optional[str] = None

    amount_type: str
    tax_included_amount: Decimal
    tax_excluded_amount: Decimal

    result_status: str
    created_at: datetime
    updated_at: datetime


# ============================================================
# Result Detail Models
# ============================================================
class ResultDetailResponse(BaseModel):
    id: int
    result_code: str

    source_record_type: str
    source_record_id: int

    billing_period: str
    billing_date: Optional[date] = None

    project_code: str
    project_name: Optional[str] = None

    contract_id: Optional[int] = None
    contract_code: Optional[str] = None
    contract_name: Optional[str] = None

    rule_id: Optional[int] = None
    rule_code: Optional[str] = None
    rule_name: Optional[str] = None

    input_amount: Decimal
    amount_type: str
    tax_included_amount: Decimal
    tax_excluded_amount: Decimal
    tax_rate: Decimal

    result_status: str
    version_no: str

    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    remarks: Optional[str] = None

    details: List[ResultDetailItemResponse] = Field(default_factory=list)
    category_summary: List[ResultCategorySummaryItemResponse] = Field(default_factory=list)
    workflow_logs: List[WorkflowLogItemResponse] = Field(default_factory=list)


# ============================================================
# Project Summary Models
# ============================================================
class ProjectSummaryItemResponse(BaseModel):
    billing_period: str
    project_code: str
    project_name: Optional[str] = None

    result_count: int

    total_tax_included_amount: Decimal
    total_tax_excluded_amount: Decimal

    category_summary: List[ResultCategorySummaryItemResponse] = Field(default_factory=list)


# ============================================================
# Query Request Models
# ============================================================
class ResultListQueryRequest(BaseModel):
    billing_period: Optional[str] = Field(default=None, min_length=7, max_length=16)
    project_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    project_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    contract_code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    contract_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    rule_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    result_status: Optional[str] = Field(default=None, min_length=1, max_length=32)
    limit: int = Field(default=100, ge=1, le=500)


class ProjectSummaryQueryRequest(BaseModel):
    billing_period: Optional[str] = Field(default=None, min_length=7, max_length=16)
    project_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    limit: int = Field(default=100, ge=1, le=500)


class WorkflowQueryRequest(BaseModel):
    business_key: str = Field(..., min_length=2, max_length=128)
    limit: int = Field(default=100, ge=1, le=500)


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