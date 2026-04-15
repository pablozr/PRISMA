from typing import TypedDict

from pydantic import BaseModel


class ProjectAreaLinkData(TypedDict):
    project_id: int
    area_id: int


class ProjectAreaLinkCreateRequest(BaseModel):
    project_id: int
    area_id: int


class ProjectAreaLinkCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectAreaLinkData]
