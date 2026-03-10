from typing import Any, Optional
from pydantic import BaseModel

class APIResponse(BaseModel):
    """统一 API 响应结构 """
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None