from typing import TypedDict


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
