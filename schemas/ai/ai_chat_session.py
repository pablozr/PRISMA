from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel


class AiChatSessionData(TypedDict):
    id: int
    user_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


class AiChatSessionCreateRequest(BaseModel):
    user_id: int
    title: Optional[str] = None


class AiChatSessionCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AiChatSessionData]
