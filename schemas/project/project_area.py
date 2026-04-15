from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel


class ProjectAreaData(TypedDict):
    id: int
    name: str
    slug: str
    created_at: datetime


class ProjectAreaCreateRequest(BaseModel):
    name: str
    slug: str


class ProjectAreaCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectAreaData]
