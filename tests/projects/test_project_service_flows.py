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
                centro_ids=[4],
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
        centro_ids=[4],
        unidade_ids=[5],
        curso_ids=[8],
        ordenacao="data_desc",
        page=1,
        page_size=100,
        somente_habilitados=True,
        q="ciencia",
    )


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


def test_get_my_project_detail_includes_authorization_context(monkeypatch: pytest.MonkeyPatch) -> None:
    repository_mock = AsyncMock(return_value={"id": 22, "institutional": {}, "editorial": {}, "opportunities": []})
    monkeypatch.setattr(project_service, "get_user_managed_project_by_id", repository_mock)
    conn = object()

    result = asyncio.run(
        project_service.get_my_project_detail(
            conn=conn, user={"id": 11, "role": "professor"}, project_id=22
        )
    )

    assert result["status"] is True
    assert result["data"]["projeto"]["access"] == {"can_edit": True, "role": "professor"}
    repository_mock.assert_awaited_once_with(conn, 22, 11, "professor")


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
