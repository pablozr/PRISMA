from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel


class OrganizationalUnitData(TypedDict):
    id: int
    nome: str
    sigla: Optional[str]
    tipo: str
    parent_unit_id: Optional[int]
    is_active: bool
    created_at: datetime


class CatalogUnitsQueryRequest(BaseModel):
    centro_ids: Optional[list[int]] = None


class CatalogUnitsData(TypedDict):
    unidades: list[OrganizationalUnitData]


class CatalogUnitsResponse(TypedDict):
    status: bool
    message: str
    data: CatalogUnitsData


class CatalogCentersData(TypedDict):
    centros: list[OrganizationalUnitData]


class CatalogCentersResponse(TypedDict):
    status: bool
    message: str
    data: CatalogCentersData
