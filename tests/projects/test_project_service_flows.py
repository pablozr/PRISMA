import asyncio
import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from schemas.project.project import ProjectListQueryRequest, ProjectUpdateRequest
from services.project import project_service


class _DummyTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummyConn:
    def transaction(self):
        return _DummyTransaction()


def test_list_projects_uses_normalized_query(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_mock = AsyncMock(return_value=([{"id": 1, "title": "Projeto"}], 3))
    monkeypatch.setattr(project_service, "get_public_projects", repo_mock)
    conn = object()

    result = asyncio.run(
        project_service.list_projects(
            conn=conn,
            query=ProjectListQueryRequest(
                area_ids=[3],
                unidade_ids=[5],
                curso_ids=[8],
                page=1,
                page_size=100,
                somente_habilitados=True,
                q="ciencia",
            ),
        )
    )

    assert result["status"] is True
    assert result["data"]["paginacao"] == {"page": 1, "page_size": 100, "total": 3, "total_pages": 1}
    repo_mock.assert_awaited_once_with(
        conn=conn,
        area_ids=[3],
        unidade_ids=[5],
        curso_ids=[8],
        ordenacao="data_desc",
        page=1,
        page_size=100,
        somente_habilitados=True,
        q="ciencia",
    )


def test_list_project_assignments_returns_not_found_when_project_does_not_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_service, "get_public_project_assignments", AsyncMock(return_value=[]))
    monkeypatch.setattr(project_service, "exists_public_project", AsyncMock(return_value=False))

    result = asyncio.run(project_service.list_project_assignments(object(), 10))

    assert result["status"] is False
    assert result["message"] == "Projeto nao encontrado."


def test_list_project_assignments_returns_empty_list_when_project_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_service, "get_public_project_assignments", AsyncMock(return_value=[]))
    monkeypatch.setattr(project_service, "exists_public_project", AsyncMock(return_value=True))

    result = asyncio.run(project_service.list_project_assignments(object(), 10))

    assert result["status"] is True
    assert result["data"] == {"atribuicoes": []}


def test_update_my_project_requires_allowed_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    update_mock = AsyncMock()
    monkeypatch.setattr(project_service, "update_managed_project_fields", update_mock)

    result = asyncio.run(
        project_service.update_my_project(
            conn=object(),
            user={"id": 11, "role": "professor"},
            project_id=22,
            data=ProjectUpdateRequest(),
        )
    )

    assert result["status"] is False
    assert result["message"] == "Nenhum campo valido informado para atualizacao."
    update_mock.assert_not_awaited()


def test_update_my_project_maps_fields_and_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    update_mock = AsyncMock(return_value={"id": 22, "title": "Novo titulo"})
    monkeypatch.setattr(project_service, "update_managed_project_fields", update_mock)

    payload = ProjectUpdateRequest(
        descricao="Descricao valida com tamanho",
        descricao_curta="Resumo valido do projeto",
    )
    conn = object()

    result = asyncio.run(
        project_service.update_my_project(
            conn=conn,
            user={"id": 11, "role": "professor"},
            project_id=22,
            data=payload,
        )
    )

    assert result["status"] is True
    assert result["data"]["projeto"]["id"] == 22
    update_mock.assert_awaited_once_with(
        conn=conn,
        project_id=22,
        user_id=11,
        user_role="professor",
            allowed_fields={
                "local_description": "Descricao valida com tamanho",
                "local_short_description": "Resumo valido do projeto",
            },
    )


def test_create_my_project_assignment_returns_error_when_course_linkage_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = _DummyConn()
    monkeypatch.setattr(
        project_service,
        "create_project_assignment",
        AsyncMock(
            return_value={
                "has_project_access": True,
                "valid_course_count": 1,
                "requested_course_count": 2,
                "assignment": None,
            }
        ),
    )

    result = asyncio.run(
        project_service.create_my_project_assignment(
            conn=conn,
            user={"id": 9, "role": "professor"},
            project_id=40,
            descricao="Descricao valida",
            curso_ids=[1, 2],
        )
    )

    assert result["status"] is False
    assert result["message"] == "Todos os cursos devem estar vinculados ao projeto."


def test_delete_my_project_assignment_returns_not_found_or_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    deactivate_mock = AsyncMock(return_value=False)
    monkeypatch.setattr(project_service, "deactivate_project_assignment", deactivate_mock)
    conn = object()

    result = asyncio.run(
        project_service.delete_my_project_assignment(
            conn=conn,
            user={"id": 8, "role": "professor"},
            assignment_id=99,
        )
    )

    assert result["status"] is False
    assert result["message"] == "Atribuicao nao encontrada ou sem permissao."
    deactivate_mock.assert_awaited_once_with(
        conn=conn,
        assignment_id=99,
        user_id=8,
        user_role="professor",
    )
