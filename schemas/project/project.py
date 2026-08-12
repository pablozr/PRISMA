from datetime import datetime
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
    sie_project_id: int
    process_code: Optional[str]
    title: str
    institutional: dict
    editorial: dict
    opportunities: list[dict]
    published_at: Optional[datetime]


class ProjectListQueryRequest(BaseProjectRequestModel):
    q: Optional[str] = Field(default=None, min_length=1, max_length=PROJECT_SEARCH_MAX_LENGTH)
    area_ids: Optional[list[int]] = None
    centro_ids: Optional[list[int]] = None
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

    @field_validator("area_ids", "centro_ids", "unidade_ids", "curso_ids")
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
    centro_ids: Optional[List[int]] = None,
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
        centro_ids=centro_ids,
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
        max_length=PROJECT_DESCRIPTION_MAX_LENGTH,
    )
    descricao_curta: Optional[str] = Field(
        default=None,
        max_length=PROJECT_DESCRIPTION_MAX_LENGTH,
    )

    @field_validator("descricao", "descricao_curta")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) < PROJECT_DESCRIPTION_MIN_LENGTH:
            raise ValueError(
                f"O campo deve ter ao menos {PROJECT_DESCRIPTION_MIN_LENGTH} caracteres."
            )
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
