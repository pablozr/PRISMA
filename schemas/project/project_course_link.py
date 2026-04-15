from typing import TypedDict

from pydantic import BaseModel


class ProjectCourseLinkData(TypedDict):
    project_id: int
    course_id: int


class ProjectCourseLinkCreateRequest(BaseModel):
    project_id: int
    course_id: int


class ProjectCourseLinkCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectCourseLinkData]
