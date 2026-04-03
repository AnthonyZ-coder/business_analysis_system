from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from app.common.enums import NextStep, RecordStatus, RuleStatus, SourceType


class FileUploadResponse(BaseModel):
    id: int
    file_uuid: str
    file_name: str
    file_type: str
    storage_path: str
    file_size: int
    file_hash: str
    mime_type: Optional[str] = None
    upload_time: datetime
    uploader: Optional[str] = None
    parse_status: str


class BaseCreateRequest(BaseModel):
    source_type: SourceType = SourceType.MANUAL
    source_system: Optional[str] = Field(default=None, max_length=100)
    operator: Optional[str] = Field(default=None, max_length=100)
    remarks: Optional[str] = None


class ProjectCreateRequest(BaseCreateRequest):
    project_code: str = Field(..., min_length=2, max_length=64)
    project_name: str = Field(..., min_length=2, max_length=255)
    customer_name: str = Field(..., min_length=2, max_length=255)
    total_amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="CNY", min_length=3, max_length=10)


class ContractCreateRequest(BaseCreateRequest):
    contract_code: str = Field(..., min_length=2, max_length=64)
    contract_name: str = Field(..., min_length=2, max_length=255)
    project_code: str = Field(..., min_length=2, max_length=64)
    customer_name: str = Field(..., min_length=2, max_length=255)
    contract_amount: Decimal = Field(..., gt=0)
    tax_included: bool = True
    sign_date: Optional[date] = None
    file_record_id: Optional[int] = None


class BillingRecordCreateRequest(BaseCreateRequest):
    billing_code: str = Field(..., min_length=2, max_length=64)
    project_code: str = Field(..., min_length=2, max_length=64)
    contract_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    billing_date: date
    billing_amount: Decimal = Field(..., gt=0)
    billing_ratio: Optional[Decimal] = Field(default=None, ge=0, le=1)
    phase_name: Optional[str] = Field(default=None, max_length=100)
    tax_included: bool = True
    file_record_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_logic(self):
        if self.billing_ratio is not None and self.billing_ratio > Decimal("1"):
            raise ValueError("billing_ratio cannot be greater than 1")
        return self


class BaseRecordResponse(BaseModel):
    id: int
    status: str
    rule_status: str
    rule_template_code: Optional[str] = None
    next_step: str
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectResponse(BaseRecordResponse):
    project_code: str
    project_name: str
    customer_name: str
    total_amount: Decimal
    currency: str
    source_type: str


class ContractResponse(BaseRecordResponse):
    contract_code: str
    contract_name: str
    project_code: str
    customer_name: str
    contract_amount: Decimal
    tax_included: bool
    sign_date: Optional[date] = None
    file_record_id: Optional[int] = None
    parse_status: str


class BillingRecordResponse(BaseRecordResponse):
    billing_code: str
    project_code: str
    contract_code: Optional[str] = None
    billing_date: date
    billing_amount: Decimal
    billing_ratio: Optional[Decimal] = None
    phase_name: Optional[str] = None
    tax_included: bool
    file_record_id: Optional[int] = None


class InternalPayloadResponse(BaseModel):
    """
    Reserved payload format for downstream modules.
    For example:
    - contract_parsing
    - product_split
    - phase_income_calc
    """

    record_type: str
    record_id: int
    business_key: str
    status: str
    next_step: str
    payload: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
    trace: Dict[str, Any] = Field(default_factory=dict)

class ContractUpdateRequest(BaseCreateRequest):
    contract_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    contract_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    customer_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    contract_amount: Optional[Decimal] = Field(default=None, gt=0)
    tax_included: Optional[bool] = None
    sign_date: Optional[date] = None
    file_record_id: Optional[int] = None    