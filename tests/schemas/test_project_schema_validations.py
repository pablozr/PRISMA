import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from schemas.project.project import ProjectListQueryRequest, ProjectUpdateRequest
from schemas.project.project_assignment import ProjectAssignmentCreateRequest


def test_project_update_request_strips_valid_fields() -> None:
    payload = ProjectUpdateRequest(
        descricao="  Descricao valida para projeto  ",
        descricao_curta="  Resumo valido do projeto  ",
    )

    assert payload.descricao == "Descricao valida para projeto"
    assert payload.descricao_curta == "Resumo valido do projeto"


def test_project_update_request_normalizes_blank_to_explicit_clear() -> None:
    payload = ProjectUpdateRequest(descricao="   ")

    assert payload.descricao is None
    assert "descricao" in payload.model_fields_set


def test_project_assignment_request_rejects_duplicate_course_ids() -> None:
    with pytest.raises(ValidationError):
        ProjectAssignmentCreateRequest(
            descricao="Descricao valida para atribuicao",
            curso_ids=[1, 1],
        )


def test_project_assignment_request_rejects_non_positive_course_ids() -> None:
    with pytest.raises(ValidationError):
        ProjectAssignmentCreateRequest(
            descricao="Descricao valida para atribuicao",
            curso_ids=[0, 2],
        )


def test_project_list_query_request_normalizes_ids_and_blank_query() -> None:
    payload = ProjectListQueryRequest(
        q="   ",
        area_ids=[3, 1, 3],
        centro_ids=[6, 4, 6],
        unidade_ids=[5, 2],
        curso_ids=[9, 9, 1],
    )

    assert payload.q is None
    assert payload.area_ids == [1, 3]
    assert payload.centro_ids == [4, 6]
    assert payload.unidade_ids == [2, 5]
    assert payload.curso_ids == [1, 9]


def test_project_list_query_request_rejects_invalid_sort_option() -> None:
    with pytest.raises(ValidationError):
        ProjectListQueryRequest(ordenacao="invalida")
