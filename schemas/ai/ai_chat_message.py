from datetime import datetime
from typing import Literal, TypedDict

from pydantic import BaseModel


class AiChatMessageData(TypedDict):
    id: int
    session_id: int
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class AiChatMessageCreateRequest(BaseModel):
    session_id: int
    role: Literal["user", "assistant", "system"]
    content: str


class AiChatMessageCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AiChatMessageData]
