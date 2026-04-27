from typing import Optional, TypedDict
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseProjectImageRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectLogoUploadRequest(BaseProjectImageRequestModel):
    image_url: str = Field(min_length=1, max_length=2048)
    alt_text: Optional[str] = Field(default=None, max_length=255)

    @field_validator("image_url")
    @classmethod
    def strip_image_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("A URL da imagem nao pode ser vazia.")

        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("A URL da imagem deve usar HTTP ou HTTPS.")

        return normalized

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
