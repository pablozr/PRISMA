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

from services.catalogue import catalogue_service


def test_get_unidades_normalizes_ids_and_sanitizes_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    repo_mock = AsyncMock(return_value=[{"id": 10, "name": "Unidade Teste"}])
    monkeypatch.setattr(catalogue_service, "get_all_unidades", repo_mock)

    result = asyncio.run(
        catalogue_service.get_unidades(
            conn,
            centro_ids=[3, 2, 3, -5, 0],
            limit=999,
            offset=-20,
        )
    )

    assert result["status"] is True
    assert result["data"] == [{"id": 10, "name": "Unidade Teste"}]
    repo_mock.assert_awaited_once_with(
        conn,
        centro_ids=[2, 3],
        limit=100,
        offset=0,
    )


def test_get_cursos_returns_failure_when_repository_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    monkeypatch.setattr(catalogue_service, "get_all_cursos", AsyncMock(return_value=[]))

    result = asyncio.run(catalogue_service.get_cursos(conn, unidade_ids=None, limit=50, offset=0))

    assert result["status"] is False
    assert result["data"] == []
    assert "Sem cursos" in result["message"]


def test_get_centros_returns_error_response_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()

    async def raise_error(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(catalogue_service, "get_all_centros", raise_error)

    result = asyncio.run(catalogue_service.get_centros(conn, limit=10, offset=0))

    assert result["status"] is False
    assert result["data"] == []
    assert "Erro ao recuperar centros" in result["message"]
