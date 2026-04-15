from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel


class CourseData(TypedDict):
    id: int
    unidade_id: Optional[int]
    nome: str
    nivel: Optional[str]
    codigo: Optional[str]
    is_active: bool
    created_at: datetime


class CatalogCoursesQueryRequest(BaseModel):
    unidade_ids: Optional[list[int]] = None


class CatalogCoursesData(TypedDict):
    cursos: list[CourseData]


class CatalogCoursesResponse(TypedDict):
    status: bool
    message: str
    data: CatalogCoursesData


class CourseCreateRequest(BaseModel):
    nome: str
    unidade_id: int


class CourseCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, CourseData]
