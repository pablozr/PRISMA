from datetime import datetime
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel


class ImportBatchData(TypedDict):
    id: int
    reference_year: int
    reference_term: Literal[1, 2]
    uploaded_by_user_id: int
    source_filename: str
    source_hash: str
    status: Literal["processing", "success", "partial", "failed"]
    total_rows: int
    imported_rows: int
    rejected_rows: int
    created_at: datetime
    finished_at: Optional[datetime]


class ImportBatchCreateRequest(BaseModel):
    reference_year: int
    reference_term: Literal[1, 2]
    uploaded_by_user_id: int
    source_filename: str
    source_hash: str
    status: Literal["processing", "success", "partial", "failed"] = "processing"
    total_rows: int = 0
    imported_rows: int = 0
    rejected_rows: int = 0
    finished_at: Optional[datetime] = None


class ImportBatchCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ImportBatchData]
