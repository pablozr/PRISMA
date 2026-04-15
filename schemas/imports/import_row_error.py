from datetime import datetime
from typing import Any, Optional, TypedDict

from pydantic import BaseModel


class ImportRowErrorData(TypedDict):
    id: int
    import_batch_id: int
    row_number: int
    raw_payload: Optional[dict[str, Any]]
    error_reason: str
    created_at: datetime


class ImportRowErrorCreateRequest(BaseModel):
    import_batch_id: int
    row_number: int
    raw_payload: Optional[dict[str, Any]]
    error_reason: str


class ImportRowErrorCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ImportRowErrorData]
