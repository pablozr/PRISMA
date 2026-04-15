from datetime import datetime
from typing import Optional, TypedDict


class ImportBatchData(TypedDict):
    id: int
    reference_year: int
    reference_term: int
    uploaded_by_user_id: int
    source_filename: str
    source_hash: str
    status: str
    total_rows: int
    imported_rows: int
    rejected_rows: int
    created_at: datetime
    finished_at: Optional[datetime]


class AdminProjectImportCsvDataResponse(TypedDict):
    import_batch_id: int
    status: str
    total_rows: int
    imported_rows: int
    rejected_rows: int


class AdminProjectImportCsvResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AdminProjectImportCsvDataResponse]
