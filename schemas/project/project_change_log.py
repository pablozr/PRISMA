from datetime import datetime
from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel


class ProjectChangeLogData(TypedDict):
    id: int
    project_id: int
    changed_by_user_id: int
    change_type: Literal["manual_edit", "status_change", "import_override"]
    field_name: str
    old_value: Optional[dict[str, Any]]
    new_value: Optional[dict[str, Any]]
    reason: Optional[str]
    created_at: datetime


class ProjectChangeLogCreateRequest(BaseModel):
    project_id: int
    changed_by_user_id: int
    change_type: Literal["manual_edit", "status_change", "import_override"]
    field_name: str
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    reason: Optional[str] = None


class ProjectChangeLogCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectChangeLogData]
