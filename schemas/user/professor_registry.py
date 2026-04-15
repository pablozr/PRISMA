from datetime import datetime
from typing import Optional, TypedDict


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
