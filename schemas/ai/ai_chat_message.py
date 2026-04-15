from datetime import datetime
from typing import TypedDict


class AiChatMessageData(TypedDict):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime
