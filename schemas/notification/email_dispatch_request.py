from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator


CONTACT_EMAIL_SUBJECT_MAX_LENGTH = 180
CONTACT_EMAIL_BODY_MAX_LENGTH = 5000


class ContactEmailCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int = Field(..., ge=1)
    subject: str = Field(..., min_length=1, max_length=CONTACT_EMAIL_SUBJECT_MAX_LENGTH)
    body: str = Field(..., min_length=1, max_length=CONTACT_EMAIL_BODY_MAX_LENGTH)

    @field_validator("subject", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O campo nao pode ser vazio.")

        return normalized


class ContactEmailCreateDataResponse(TypedDict):
    request_id: int
    status: str


class ContactEmailCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ContactEmailCreateDataResponse]


class ContactEmailStatusDataResponse(TypedDict):
    request_id: int
    status: str
    attempt_count: int
    next_attempt_at: Optional[datetime]
    last_error: Optional[str]
    sent_at: Optional[datetime]


class ContactEmailStatusResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ContactEmailStatusDataResponse]
