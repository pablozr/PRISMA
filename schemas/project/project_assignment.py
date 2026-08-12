from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

ASSIGNMENT_DESCRIPTION_MIN_LENGTH = 10
ASSIGNMENT_DESCRIPTION_MAX_LENGTH = 1000


class BaseProjectAssignmentRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectAssignmentCreateRequest(BaseProjectAssignmentRequestModel):
    descricao: str = Field(
        min_length=ASSIGNMENT_DESCRIPTION_MIN_LENGTH,
        max_length=ASSIGNMENT_DESCRIPTION_MAX_LENGTH,
    )
    curso_ids: list[int] = Field(min_length=1)

    @field_validator("descricao")
    @classmethod
    def strip_descricao(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("A descricao nao pode ser vazia.")
        return normalized

    @field_validator("curso_ids")
    @classmethod
    def normalize_curso_ids(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("Os IDs de curso nao podem conter duplicados.")

        if any(course_id <= 0 for course_id in value):
            raise ValueError("Os IDs de curso devem ser inteiros positivos.")

        return sorted(value)


class ProjectAssignmentData(TypedDict):
    atribuicao_id: int
    projeto_id: int
    descricao: str
    curso_ids: list[int]


class ProjectOpportunityData(TypedDict):
    id: int
    project_id: int
    description: str
    courses: list[dict]


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
