from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    max_preview_chars: int = Field(default=2000, ge=100, le=10000)
    max_pages: Optional[int] = Field(default=None, ge=1, le=500)
    force_reparse: bool = False


class ParseResultResponse(BaseModel):
    record_type: str
    record_id: int
    file_record_id: int
    parse_status: str
    file_parse_status: str
    file_name: str
    storage_path: str
    extracted_text_length: int
    extracted_page_count: int
    text_preview: str
    warnings: List[str] = Field(default_factory=list)
    parsed_at: Optional[datetime] = None
    ext: Dict[str, Any] = Field(default_factory=dict)


class InternalPayloadResponse(BaseModel):
    record_type: str
    record_id: int
    business_key: str
    status: str
    next_step: str
    payload: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
    trace: Dict[str, Any] = Field(default_factory=dict)