from datetime import date, datetime
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel


class ProjectData(TypedDict):
    id: int
    process_code: Optional[str]
    title: str
    short_description: Optional[str]
    full_description: Optional[str]
    contact_email: str
    owner_professor_id: int
    executing_unit_id: Optional[int]
    source_import_batch_id: Optional[int]
    status: Literal["draft", "published", "archived"]
    is_active: bool
    starts_at: Optional[date]
    ends_at: Optional[date]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    deactivated_at: Optional[datetime]


class ProjectCreateRequest(BaseModel):
    process_code: Optional[str] = None
    title: str
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    contact_email: str
    owner_professor_id: int
    executing_unit_id: Optional[int] = None
    source_import_batch_id: Optional[int] = None
    status: Literal["draft", "published", "archived"] = "draft"
    is_active: bool = True
    starts_at: Optional[date] = None
    ends_at: Optional[date] = None
    published_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None


class ProjectCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectData]
