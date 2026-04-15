from datetime import datetime
from typing import Any, Optional, TypedDict


class ProjectChangeLogData(TypedDict):
    id: int
    project_id: int
    changed_by_user_id: int
    change_type: str
    field_name: str
    old_value: Optional[dict[str, Any]]
    new_value: Optional[dict[str, Any]]
    reason: Optional[str]
    created_at: datetime
