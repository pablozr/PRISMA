from datetime import datetime
from typing import Optional, TypedDict


class ProjectImageData(TypedDict):
    id: int
    project_id: int
    image_type: str
    image_url: str
    alt_text: Optional[str]
    sort_order: int
    created_at: datetime


class ProjectLogoUploadDataResponse(TypedDict):
    projeto_id: int
    image_url: str
    alt_text: Optional[str]


class ProjectLogoUploadResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectLogoUploadDataResponse]
