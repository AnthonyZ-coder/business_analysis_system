from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Result Detail Models
# ============================================================
class ResultStorageDetailResponse(BaseModel):
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


# ============================================================
# Result Record Models
# ============================================================
class ResultStorageCreateFromPhaseIncomeRequest(BaseModel):
    created_by: Optional[str] = Field(default=None, max_length=64)
    remarks: Optional[str] = None


class ResultStorageRecordResponse(BaseModel):
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

    details: List[ResultStorageDetailResponse] = Field(default_factory=list)


# ============================================================
# Workflow Status Log Models
# ============================================================
class WorkflowStatusLogCreateRequest(BaseModel):
    business_key: str = Field(..., min_length=2, max_length=128)
    business_type: str = Field(..., min_length=2, max_length=64)

    source_module: str = Field(..., min_length=2, max_length=64)

    from_status: Optional[str] = Field(default=None, max_length=64)
    to_status: str = Field(..., min_length=2, max_length=64)

    action_type: Optional[str] = Field(default=None, max_length=64)
    operator: Optional[str] = Field(default=None, max_length=64)

    related_record_type: Optional[str] = Field(default=None, max_length=64)
    related_record_id: Optional[int] = None

    message: Optional[str] = None
    ext_json: Optional[Dict[str, Any]] = None


class WorkflowStatusLogResponse(BaseModel):
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