from datetime import datetime
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel


class OrganizationalUnitData(TypedDict):
    id: int
    name: str
    short_name: Optional[str]
    type: Literal["centro", "departamento", "instituto"]
    parent_unit_id: Optional[int]
    is_active: bool
    created_at: datetime


class OrganizationalUnitCreateRequest(BaseModel):
    name: str
    short_name: Optional[str] = None
    type: Literal["centro", "departamento", "instituto"]
    parent_unit_id: Optional[int] = None
    is_active: bool = True


class OrganizationalUnitCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, OrganizationalUnitData]
