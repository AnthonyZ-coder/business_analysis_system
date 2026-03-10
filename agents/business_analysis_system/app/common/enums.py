from enum import Enum


class SourceType(str, Enum):
    MANUAL = "MANUAL"
    API = "API"
    IMPORT = "IMPORT"
    MOCK = "MOCK"


class RecordStatus(str, Enum):
    DRAFT = "DRAFT"
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    READY_FOR_NEXT = "READY_FOR_NEXT"
    ERROR = "ERROR"


class RuleStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    PLACEHOLDER_MATCHED = "PLACEHOLDER_MATCHED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"


class NextStep(str, Enum):
    CONTRACT_PARSE = "CONTRACT_PARSE"
    PRODUCT_SPLIT = "PRODUCT_SPLIT"
    PHASE_INCOME_CALC = "PHASE_INCOME_CALC"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    NONE = "NONE"


class FileType(str, Enum):
    CONTRACT_PDF = "contract_pdf"
    BILLING_PDF = "billing_pdf"


class ParseStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"