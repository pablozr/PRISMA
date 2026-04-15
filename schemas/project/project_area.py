from datetime import datetime
from typing import TypedDict


class ProjectAreaData(TypedDict):
    id: int
    name: str
    slug: str
    created_at: datetime


class CatalogProjectAreasDataResponse(TypedDict):
    areas: list[ProjectAreaData]


class CatalogProjectAreasResponse(TypedDict):
    status: bool
    message: str
    data: CatalogProjectAreasDataResponse
