from datetime import date, datetime
from typing import List, Literal, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.config.config import (
    PROJECTS_DEFAULT_ONLY_ENABLED,
    PROJECTS_DEFAULT_PAGE,
    PROJECTS_DEFAULT_PAGE_SIZE,
    PROJECTS_DEFAULT_SORT,
    PROJECTS_MAX_PAGE_SIZE,
)

PROJECT_TITLE_MIN_LENGTH = 3
PROJECT_TITLE_MAX_LENGTH = 255
PROJECT_DESCRIPTION_MIN_LENGTH = 10
PROJECT_DESCRIPTION_MAX_LENGTH = 10000
PROJECT_SEARCH_MAX_LENGTH = 255


class BaseProjectRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectData(TypedDict):
    id: int
    process_code: Optional[str]
    title: str
    short_description: Optional[str]
    full_description: Optional[str]
    contact_email: str
    owner_professor_id: int
    owner_professor_name: Optional[str]
    responsible_id: Optional[int]
    responsible_name: Optional[str]
    responsible_email: Optional[str]
    responsible_type: Optional[str]
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
    cover_image_id: Optional[int]
    cover_image_url: Optional[str]
    cover_image_alt_text: Optional[str]


class ProjectListQueryRequest(BaseProjectRequestModel):
    q: Optional[str] = Field(default=None, min_length=1, max_length=PROJECT_SEARCH_MAX_LENGTH)
    area_ids: Optional[list[int]] = None
    unidade_ids: Optional[list[int]] = None
    curso_ids: Optional[list[int]] = None
    ordenacao: Literal["titulo_asc", "titulo_desc", "data_desc"] = PROJECTS_DEFAULT_SORT
    page: int = Field(default=PROJECTS_DEFAULT_PAGE, ge=1)
    page_size: int = Field(default=PROJECTS_DEFAULT_PAGE_SIZE, ge=1, le=PROJECTS_MAX_PAGE_SIZE)
    somente_habilitados: bool = PROJECTS_DEFAULT_ONLY_ENABLED

    @field_validator("q")
    @classmethod
    def strip_query(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @field_validator("area_ids", "unidade_ids", "curso_ids")
    @classmethod
    def normalize_positive_ids(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        if value is None:
            return None

        normalized = sorted(set(value))
        if any(item <= 0 for item in normalized):
            raise ValueError("Os IDs devem ser inteiros positivos.")

        return normalized or None


class ProjectManagedListQueryRequest(BaseProjectRequestModel):
    q: Optional[str] = Field(default=None, min_length=1, max_length=PROJECT_SEARCH_MAX_LENGTH)
    page: int = Field(default=PROJECTS_DEFAULT_PAGE, ge=1)
    page_size: int = Field(default=PROJECTS_DEFAULT_PAGE_SIZE, ge=1, le=PROJECTS_MAX_PAGE_SIZE)

    @field_validator("q")
    @classmethod
    def strip_query(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


def build_project_list_query_request(
    q: Optional[str] = None,
    area_ids: Optional[List[int]] = None,
    unidade_ids: Optional[List[int]] = None,
    curso_ids: Optional[List[int]] = None,
    ordenacao: str = PROJECTS_DEFAULT_SORT,
    page: int = PROJECTS_DEFAULT_PAGE,
    page_size: int = PROJECTS_DEFAULT_PAGE_SIZE,
    somente_habilitados: bool = PROJECTS_DEFAULT_ONLY_ENABLED,
) -> ProjectListQueryRequest:
    return ProjectListQueryRequest(
        q=q,
        area_ids=area_ids,
        unidade_ids=unidade_ids,
        curso_ids=curso_ids,
        ordenacao=ordenacao,
        page=page,
        page_size=page_size,
        somente_habilitados=somente_habilitados,
    )


def build_project_managed_list_query_request(
    q: Optional[str] = None,
    page: int = PROJECTS_DEFAULT_PAGE,
    page_size: int = PROJECTS_DEFAULT_PAGE_SIZE,
) -> ProjectManagedListQueryRequest:
    return ProjectManagedListQueryRequest(q=q, page=page, page_size=page_size)


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


class ProjectUpdateRequest(BaseProjectRequestModel):
    descricao: Optional[str] = Field(
        default=None,
        min_length=PROJECT_DESCRIPTION_MIN_LENGTH,
        max_length=PROJECT_DESCRIPTION_MAX_LENGTH,
    )
    descricao_curta: Optional[str] = Field(
        default=None,
        min_length=PROJECT_DESCRIPTION_MIN_LENGTH,
        max_length=PROJECT_DESCRIPTION_MAX_LENGTH,
    )

    @field_validator("descricao", "descricao_curta")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        normalized = value.strip()
        if not normalized:
            raise ValueError("O campo nao pode ser vazio.")

        return normalized


class ProjectUpdateResponse(TypedDict):
    status: bool
    message: str
    data: ProjectDetailDataResponse


class ProjectStatusUpdateRequest(BaseProjectRequestModel):
    habilitado: bool


class ProjectStatusUpdateDataResponse(TypedDict):
    projeto_id: int
    habilitado: bool


class ProjectStatusUpdateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectStatusUpdateDataResponse]
