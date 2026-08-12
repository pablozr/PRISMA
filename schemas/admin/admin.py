from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminBaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AdminUsersListQuery(AdminBaseSchema):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: Optional[str] = Field(default=None, min_length=1, max_length=255)

    @field_validator("q")
    @classmethod
    def strip_query(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminUserUpdateRequest(AdminBaseSchema):
    role: Optional[Literal["admin", "professor", "tecnico", "aluno"]] = None
    is_active: Optional[bool] = None


class AdminProjectsListQuery(AdminBaseSchema):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: Optional[str] = Field(default=None, min_length=1, max_length=255)

    @field_validator("q")
    @classmethod
    def strip_query(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminProjectUpdateRequest(AdminBaseSchema):
    publication_status: Optional[Literal["draft", "published", "archived"]] = None
    is_visible: Optional[bool] = None


class AdminSyncRunsListQuery(AdminBaseSchema):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AdminSyncRunErrorsListQuery(AdminBaseSchema):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
