from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel


class ContactEmailCreateRequest(BaseModel):
    project_id: int
    to_email: str
    subject: str
    body: str


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
