from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================
# Search / Query Models
# ============================================================
class ContractSearchItemResponse(BaseModel):
    contract_id: Optional[int] = None
    contract_code: Optional[str] = None
    contract_name: Optional[str] = None
    project_code: str
    project_name: Optional[str] = None
    customer_name: Optional[str] = None


class ProductSplitRuleListItemResponse(BaseModel):
    rule_id: int
    rule_code: str
    rule_name: str
    rule_type: str
    project_type_tag: Optional[str] = None
    applicable_scope: Optional[str] = None
    category_split_json: Optional[Dict[str, Any]] = None
    status: str


# ============================================================
# Detail / Summary Models
# ============================================================
class PhaseIncomeDetailResponse(BaseModel):
    id: int
    phase_income_id: int
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


class PhaseIncomeCategorySummaryResponse(BaseModel):
    id: int
    phase_income_id: int
    category_code: str
    category_name: str
    split_ratio: Decimal
    tax_included_amount: Decimal
    tax_excluded_amount: Decimal
    created_at: datetime
    updated_at: datetime
    remarks: Optional[str] = None


# ============================================================
# Create / Update Request Models
# ============================================================
class PhaseIncomeCreateRequest(BaseModel):
    billing_period: str = Field(..., min_length=7, max_length=16, description="格式建议：YYYY-MM")
    billing_date: Optional[date] = None

    project_code: str = Field(..., min_length=2, max_length=64)
    project_name: Optional[str] = Field(default=None, max_length=255)

    contract_id: Optional[int] = None
    contract_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    contract_name: Optional[str] = Field(default=None, max_length=255)

    rule_id: int = Field(..., gt=0)

    input_amount: Decimal = Field(..., gt=0)
    amount_type: str = Field(..., min_length=5, max_length=32, description="TAX_INCLUDED / TAX_EXCLUDED")

    tax_rate: Decimal = Field(default=Decimal("0.06"), ge=0, le=1)

    source_type: str = Field(default="MANUAL", min_length=2, max_length=32)
    created_by: Optional[str] = Field(default=None, max_length=64)
    remarks: Optional[str] = None

    @field_validator("billing_period")
    @classmethod
    def validate_billing_period(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 7:
            raise ValueError("billing_period format is invalid, expected like YYYY-MM")
        return value

    @field_validator("amount_type")
    @classmethod
    def validate_amount_type(cls, value: str) -> str:
        allowed = {"TAX_INCLUDED", "TAX_EXCLUDED"}
        value = value.strip().upper()
        if value not in allowed:
            raise ValueError("amount_type must be TAX_INCLUDED or TAX_EXCLUDED")
        return value

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str) -> str:
        allowed = {"MANUAL", "LLM"}
        value = value.strip().upper()
        if value not in allowed:
            raise ValueError("source_type must be MANUAL or LLM")
        return value

    @model_validator(mode="after")
    def validate_contract_identity(self):
        if self.contract_id is None and not self.contract_code and not self.contract_name:
            # 第一阶段允许只传 project_code，不强制合同
            return self
        return self


class PhaseIncomeUpdateRequest(BaseModel):
    billing_period: Optional[str] = Field(default=None, min_length=7, max_length=16)
    billing_date: Optional[date] = None

    project_name: Optional[str] = Field(default=None, max_length=255)

    contract_id: Optional[int] = None
    contract_code: Optional[str] = Field(default=None, min_length=2, max_length=64)
    contract_name: Optional[str] = Field(default=None, max_length=255)

    rule_id: Optional[int] = Field(default=None, gt=0)

    input_amount: Optional[Decimal] = Field(default=None, gt=0)
    amount_type: Optional[str] = Field(default=None, min_length=5, max_length=32)
    tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)

    calc_status: Optional[str] = Field(default=None, min_length=2, max_length=32)
    updated_by: Optional[str] = Field(default=None, max_length=64)
    remarks: Optional[str] = None

    @field_validator("amount_type")
    @classmethod
    def validate_amount_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        allowed = {"TAX_INCLUDED", "TAX_EXCLUDED"}
        value = value.strip().upper()
        if value not in allowed:
            raise ValueError("amount_type must be TAX_INCLUDED or TAX_EXCLUDED")
        return value

    @field_validator("calc_status")
    @classmethod
    def validate_calc_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        allowed = {"CALCULATED", "CONFIRMED", "CANCELLED"}
        value = value.strip().upper()
        if value not in allowed:
            raise ValueError("calc_status must be CALCULATED / CONFIRMED / CANCELLED")
        return value


# ============================================================
# Main Response Models
# ============================================================
class PhaseIncomeRecordResponse(BaseModel):
    id: int
    phase_income_code: str
    billing_period: str
    billing_date: Optional[date] = None

    project_code: str
    project_name: Optional[str] = None

    contract_id: Optional[int] = None
    contract_code: Optional[str] = None
    contract_name: Optional[str] = None

    rule_id: int
    rule_code: Optional[str] = None
    rule_name: Optional[str] = None

    input_amount: Decimal
    amount_type: str
    tax_included_amount: Decimal
    tax_excluded_amount: Decimal
    tax_rate: Decimal

    calc_status: str
    source_type: str

    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    remarks: Optional[str] = None

    details: List[PhaseIncomeDetailResponse] = Field(default_factory=list)
    category_summary: List[PhaseIncomeCategorySummaryResponse] = Field(default_factory=list)


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