from datetime import datetime
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel


class CourseData(TypedDict):
    id: int
    unit_id: Optional[int]
    name: str
    level: Literal["graduacao", "pos"]
    code: Optional[str]
    is_active: bool
    created_at: datetime


class CourseCreateRequest(BaseModel):
    unit_id: Optional[int] = None
    name: str
    level: Literal["graduacao", "pos"]
    code: Optional[str] = None
    is_active: bool = True


class CourseCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, CourseData]
