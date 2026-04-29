import asyncio
import json
import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from routes.projects import router as projects_router_module
from schemas.project.project import ProjectUpdateRequest
from schemas.project.project_assignment import ProjectAssignmentCreateRequest


def test_get_projects_forwards_filters_and_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    service_mock = AsyncMock(
        return_value={
            "status": True,
            "message": "ok",
            "data": {"projetos": [{"id": 1}], "paginacao": {"page": 2}},
        }
    )
    monkeypatch.setattr(projects_router_module, "list_projects", service_mock)

    response = asyncio.run(
        projects_router_module.get_projects(
            conn=conn,
            q="abc",
            area_ids=[1, 2],
            unidade_ids=[5],
            curso_ids=[9],
            ordenacao="titulo_asc",
            page=2,
            page_size=30,
            somente_habilitados=False,
        )
    )

    assert response.status_code == 200
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["data"]["projetos"] == [{"id": 1}]
    service_mock.assert_awaited_once()
    args = service_mock.await_args.args
    assert args[0] is conn
    assert args[1].area_ids == [1, 2]
    assert args[1].unidade_ids == [5]
    assert args[1].curso_ids == [9]
    assert args[1].ordenacao == "titulo_asc"
    assert args[1].page == 2
    assert args[1].page_size == 30
    assert args[1].somente_habilitados is False
    assert args[1].q == "abc"


def test_get_projects_returns_400_when_service_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projects_router_module,
        "list_projects",
        AsyncMock(return_value={"status": False, "message": "Ordenacao invalida.", "data": {}}),
    )

    response = asyncio.run(projects_router_module.get_projects(conn=object()))

    assert response.status_code == 400
    assert json.loads(response.body.decode("utf-8")) == {"detail": "Ordenacao invalida."}


def test_get_my_projects_forwards_authenticated_user(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 99, "role": "professor"}
    service_mock = AsyncMock(return_value={"status": True, "message": "ok", "data": {"projetos": []}})
    monkeypatch.setattr(projects_router_module, "list_my_projects", service_mock)

    response = asyncio.run(projects_router_module.get_my_projects(user=user, conn=conn, page=1, page_size=20, q=None))

    assert response.status_code == 200
    service_mock.assert_awaited_once()
    args = service_mock.await_args.args
    assert args[0] is conn
    assert args[1] is user
    assert args[2].page == 1
    assert args[2].page_size == 20
    assert args[2].q is None


def test_patch_project_passes_validated_payload_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 99, "role": "professor"}
    service_mock = AsyncMock(
        return_value={
            "status": True,
            "message": "Projeto atualizado com sucesso.",
            "data": {"projeto": {"id": 10}},
        }
    )
    monkeypatch.setattr(projects_router_module, "update_my_project", service_mock)

    payload = ProjectUpdateRequest(titulo="  Titulo valido  ", descricao="  Descricao suficientemente valida  ")

    response = asyncio.run(projects_router_module.patch_my_project(project_id=10, payload=payload, user=user, conn=conn))

    assert response.status_code == 200
    body = json.loads(response.body.decode("utf-8"))
    assert body["data"]["projeto"]["id"] == 10
    service_mock.assert_awaited_once_with(conn, user, 10, payload)
    assert payload.titulo == "Titulo valido"


def test_patch_project_returns_400_when_service_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 99, "role": "professor"}
    monkeypatch.setattr(
        projects_router_module,
        "update_my_project",
        AsyncMock(return_value={"status": False, "message": "Projeto invalido.", "data": {}}),
    )

    payload = ProjectUpdateRequest(titulo="Titulo valido")
    response = asyncio.run(projects_router_module.patch_my_project(project_id=0, payload=payload, user=user, conn=conn))

    assert response.status_code == 400
    assert json.loads(response.body.decode("utf-8")) == {"detail": "Projeto invalido."}


def test_post_project_logo_forwards_payload_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 99, "role": "professor"}
    service_mock = AsyncMock(
        return_value={
            "status": True,
            "message": "Logo do projeto atualizada com sucesso.",
            "data": {"logo": {"projeto_id": 10}},
        }
    )
    monkeypatch.setattr(projects_router_module, "upload_project_logo", service_mock)

    image = object()
    response = asyncio.run(projects_router_module.post_project_logo(project_id=10, image=image, alt_text="logo", user=user, conn=conn))

    assert response.status_code == 200
    service_mock.assert_awaited_once()
    args = service_mock.await_args.args
    assert args[0] is conn
    assert args[1] is user
    assert args[2] == 10
    assert args[3].image is image
    assert args[3].alt_text == "logo"


def test_post_project_assignment_returns_201_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 99, "role": "professor"}
    service_mock = AsyncMock(
        return_value={
            "status": True,
            "message": "Atribuicao criada com sucesso.",
            "data": {"atribuicao": {"atribuicao_id": 8}},
        }
    )
    monkeypatch.setattr(projects_router_module, "create_my_project_assignment", service_mock)

    payload = ProjectAssignmentCreateRequest(
        descricao="Descricao valida para atribuicao",
        curso_ids=[3, 2, 1],
    )
    response = asyncio.run(
        projects_router_module.post_project_assignment(project_id=10, payload=payload, user=user, conn=conn)
    )

    assert response.status_code == 201
    body = json.loads(response.body.decode("utf-8"))
    assert body["data"]["atribuicao"]["atribuicao_id"] == 8
    service_mock.assert_awaited_once_with(conn, user, 10, "Descricao valida para atribuicao", [1, 2, 3])


def test_delete_assignment_returns_400_when_service_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 99, "role": "professor"}
    monkeypatch.setattr(
        projects_router_module,
        "delete_my_project_assignment",
        AsyncMock(return_value={"status": False, "message": "Atribuicao nao encontrada", "data": {}}),
    )

    response = asyncio.run(projects_router_module.delete_project_assignment(assignment_id=77, user=user, conn=conn))

    assert response.status_code == 400
    assert json.loads(response.body.decode("utf-8")) == {"detail": "Atribuicao nao encontrada"}
