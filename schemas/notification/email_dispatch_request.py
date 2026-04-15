from datetime import datetime
from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel


class EmailDispatchRequestData(TypedDict):
    id: int
    requested_by_user_id: int
    project_id: int
    to_email: str
    subject: str
    body: str
    payload: Optional[dict[str, Any]]
    status: Literal["queued", "processing", "sent", "failed", "dead_letter"]
    attempt_count: int
    next_attempt_at: Optional[datetime]
    last_error: Optional[str]
    provider_message_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime]


class EmailDispatchRequestCreateRequest(BaseModel):
    requested_by_user_id: int
    project_id: int
    to_email: str
    subject: str
    body: str
    payload: Optional[dict[str, Any]] = None
    status: Literal["queued", "processing", "sent", "failed", "dead_letter"] = "queued"
    attempt_count: int = 0
    next_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    provider_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None


class EmailDispatchRequestCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, EmailDispatchRequestData]
