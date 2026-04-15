from datetime import datetime
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel


class ProjectImageData(TypedDict):
    id: int
    project_id: int
    image_type: Literal["cover", "gallery"]
    image_url: str
    alt_text: Optional[str]
    sort_order: int
    created_at: datetime


class ProjectImageCreateRequest(BaseModel):
    project_id: int
    image_type: Literal["cover", "gallery"]
    image_url: str
    alt_text: Optional[str] = None
    sort_order: int = 0


class ProjectImageCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectImageData]
