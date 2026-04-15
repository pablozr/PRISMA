from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel


class ProfessorRegistryData(TypedDict):
    id: int
    institutional_email: str
    full_name: str
    siape: Optional[str]
    unit_id: Optional[int]
    user_id: Optional[int]
    source_import_batch_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfessorRegistryCreateRequest(BaseModel):
    institutional_email: str
    full_name: str
    siape: Optional[str] = None
    unit_id: Optional[int] = None
    user_id: Optional[int] = None
    source_import_batch_id: Optional[int] = None
    is_active: bool = True


class ProfessorRegistryCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProfessorRegistryData]
