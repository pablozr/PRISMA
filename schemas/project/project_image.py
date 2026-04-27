from typing import Optional, TypedDict

from pydantic import BaseModel, Field


class ProjectLogoUploadRequest(BaseModel):
    image_url: str = Field(min_length=1, max_length=2048)
    alt_text: Optional[str] = Field(default=None, max_length=255)


class ProjectLogoUploadDataResponse(TypedDict):
    projeto_id: int
    image_url: str
    alt_text: Optional[str]


class ProjectLogoUploadResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectLogoUploadDataResponse]
