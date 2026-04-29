from typing import Optional, TypedDict

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectLogoUploadRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    image: UploadFile
    alt_text: Optional[str] = Field(default=None, max_length=255)

    @field_validator("alt_text")
    @classmethod
    def strip_alt_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class ProjectLogoUploadDataResponse(TypedDict):
    projeto_id: int
    image_url: str
    alt_text: Optional[str]


class ProjectLogoUploadResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectLogoUploadDataResponse]
