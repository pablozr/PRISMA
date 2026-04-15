from datetime import datetime
from typing import Optional, TypedDict


class AiChatSessionData(TypedDict):
    session_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime


class AiSessionMessageData(TypedDict):
    role: str
    content: str
    created_at: datetime


class AiChatSessionHistoryDataResponse(TypedDict):
    session: AiChatSessionData
    messages: list[AiSessionMessageData]


class AiChatSessionHistoryResponse(TypedDict):
    status: bool
    message: str
    data: AiChatSessionHistoryDataResponse
