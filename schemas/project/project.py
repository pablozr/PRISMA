from datetime import date, datetime
from typing import Optional, TypedDict

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
    status: str
    is_active: bool
    starts_at: Optional[date]
    ends_at: Optional[date]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    deactivated_at: Optional[datetime]


class ProjectListQueryRequest(BaseModel):
    q: Optional[str] = None
    area_ids: Optional[list[int]] = None
    unidade_ids: Optional[list[int]] = None
    curso_ids: Optional[list[int]] = None
    ordenacao: Optional[str] = None
    page: int = 1
    page_size: int = 20
    somente_habilitados: bool = True


class ProjectListDataResponse(TypedDict):
    projetos: list[ProjectData]


class ProjectListResponse(TypedDict):
    status: bool
    message: str
    data: ProjectListDataResponse


class ProjectDetailDataResponse(TypedDict):
    projeto: ProjectData


class ProjectDetailResponse(TypedDict):
    status: bool
    message: str
    data: ProjectDetailDataResponse


class ProjectUpdateRequest(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None


class ProjectUpdateResponse(TypedDict):
    status: bool
    message: str
    data: ProjectDetailDataResponse


class ProjectStatusUpdateRequest(BaseModel):
    habilitado: bool


class ProjectStatusUpdateDataResponse(TypedDict):
    projeto_id: int
    habilitado: bool


class ProjectStatusUpdateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectStatusUpdateDataResponse]
