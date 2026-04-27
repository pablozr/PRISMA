import os
import json
import asyncio
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from routes.catalogues import router as catalogue_router_module

def test_get_unidades_forwards_filters_and_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    service_mock = AsyncMock(
        return_value={
            "status": True,
            "message": "ok",
            "data": {"unidades": [{"id": 1}]},
        }
    )
    monkeypatch.setattr(catalogue_router_module, "service_get_unidades", service_mock)

    response = asyncio.run(
        catalogue_router_module.list_unidades(
            conn=conn,
            centro_ids=[1, 3],
            limit=10,
            offset=5,
        )
    )

    assert response.status_code == 200
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["data"] == {"unidades": [{"id": 1}]}
    service_mock.assert_awaited_once_with(conn, [1, 3], 10, 5)


def test_get_cursos_returns_400_on_service_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    monkeypatch.setattr(
        catalogue_router_module,
        "service_get_cursos",
        AsyncMock(return_value={"status": False, "message": "Sem cursos", "data": []}),
    )

    response = asyncio.run(catalogue_router_module.list_cursos(conn=conn, unidade_ids=None, limit=50, offset=0))

    assert response.status_code == 400
    assert json.loads(response.body.decode("utf-8")) == {"detail": "Sem cursos"}


def test_list_centros_uses_default_pagination_when_not_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    service_mock = AsyncMock(return_value={"status": True, "message": "ok", "data": {"centros": []}})
    monkeypatch.setattr(catalogue_router_module, "service_get_centros", service_mock)

    response = asyncio.run(catalogue_router_module.list_centros(conn=conn))

    assert response.status_code == 200
    service_mock.assert_awaited_once_with(conn, 50, 0)

def test_get_areas_tematicas_returns_500_when_service_crashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = object()

    async def raise_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(catalogue_router_module, "service_get_areas_tematicas", raise_error)

    response = asyncio.run(catalogue_router_module.list_areas_tematicas(conn=conn, limit=50, offset=0))

    assert response.status_code == 500
    assert json.loads(response.body.decode("utf-8")) == {"detail": "Erro interno com o servidor."}
