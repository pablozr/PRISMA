from datetime import date, datetime
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel


class ProjectData(TypedDict):
    id: int
    process_code: Optional[str]
    title: str
    short_description: Optional[str]
    full_description: Optional[str]
    contact_email: str
    owner_professor_id: int
    owner_professor_name: Optional[str]
    executing_unit_id: Optional[int]
    executing_unit_name: Optional[str]
    executing_unit_short_name: Optional[str]
    executing_unit_type: Optional[str]
    source_import_batch_id: Optional[int]
    project_type_id: Optional[int]
    project_type_name: Optional[str]
    project_type_slug: Optional[str]
    project_type_is_enabled: Optional[bool]
    area_ids: Optional[list[int]]
    course_ids: Optional[list[int]]
    areas: Optional[list[dict]]
    cursos: Optional[list[dict]]
    imagens: Optional[list[dict]]
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
    ordenacao: Literal["titulo_asc", "titulo_desc", "data_desc"] = "data_desc"
    page: int = 1
    page_size: int = 20
    somente_habilitados: bool = True


class ProjectPaginationData(TypedDict):
    page: int
    page_size: int
    total: int
    total_pages: int


class ProjectListDataResponse(TypedDict):
    projetos: list[ProjectData]
    paginacao: ProjectPaginationData


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
