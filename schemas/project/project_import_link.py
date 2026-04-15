from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel


class ProjectImportLinkData(TypedDict):
    project_id: int
    import_batch_id: int
    created_at: datetime


class ProjectImportLinkCreateRequest(BaseModel):
    project_id: int
    import_batch_id: int


class ProjectImportLinkCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectImportLinkData]
