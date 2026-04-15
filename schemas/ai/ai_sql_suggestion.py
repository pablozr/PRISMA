from datetime import datetime
from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel


class AiSqlSuggestionData(TypedDict):
    id: int
    session_id: int
    user_id: int
    question: str
    generated_sql: str
    validation_status: Literal["approved", "rejected"]
    validation_errors: Optional[dict[str, Any]]
    model_name: Optional[str]
    feedback_score: Optional[int]
    created_at: datetime


class AiSqlSuggestionCreateRequest(BaseModel):
    session_id: int
    user_id: int
    question: str
    generated_sql: str
    validation_status: Literal["approved", "rejected"]
    validation_errors: Optional[dict[str, Any]] = None
    model_name: Optional[str] = None
    feedback_score: Optional[int] = None


class AiSqlSuggestionCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AiSqlSuggestionData]
