from typing import TypedDict

from pydantic import BaseModel, Field


class ProjectAssignmentCreateRequest(BaseModel):
    descricao: str = Field(min_length=1, max_length=1000)
    curso_ids: list[int] = Field(min_length=1)


class ProjectAssignmentData(TypedDict):
    atribuicao_id: int
    projeto_id: int
    descricao: str
    curso_ids: list[int]


class ProjectAssignmentCreateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectAssignmentData]


class ProjectAssignmentListDataResponse(TypedDict):
    atribuicoes: list[ProjectAssignmentData]


class ProjectAssignmentListResponse(TypedDict):
    status: bool
    message: str
    data: ProjectAssignmentListDataResponse


class ProjectAssignmentDeleteDataResponse(TypedDict):
    atribuicao_id: int
    removida: bool


class ProjectAssignmentDeleteResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, ProjectAssignmentDeleteDataResponse]
