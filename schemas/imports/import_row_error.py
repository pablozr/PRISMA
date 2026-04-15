from datetime import datetime
from typing import Any, Optional, TypedDict


class ImportRowErrorData(TypedDict):
    id: int
    import_batch_id: int
    row_number: int
    raw_payload: Optional[dict[str, Any]]
    error_reason: str
    created_at: datetime
