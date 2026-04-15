from datetime import datetime
from typing import Any, Optional, TypedDict

from pydantic import BaseModel


class AiSqlSuggestionData(TypedDict):
    suggestion_id: int
    session_id: int
    question: str
    generated_sql: str
    validation_status: str
    validation_errors: Optional[dict[str, Any]]
    created_at: datetime


class AiSqlSuggestionRequest(BaseModel):
    question: str


class AiSqlSuggestionResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AiSqlSuggestionData]
