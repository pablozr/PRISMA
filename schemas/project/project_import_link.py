from datetime import datetime
from typing import TypedDict


class ProjectImportLinkData(TypedDict):
    project_id: int
    import_batch_id: int
    created_at: datetime
