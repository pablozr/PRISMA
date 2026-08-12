import asyncio
from contextlib import asynccontextmanager
from unittest.mock import ANY, AsyncMock

import pytest

from services.sie import sync_service


class Pool:
    @asynccontextmanager
    async def acquire(self):
        yield Connection()


class Connection:
    @asynccontextmanager
    async def transaction(self):
        yield


class Client:
    async def fetch_access_token(self) -> str:
        return "token"

    async def fetch_page(self, token: str, start: int, end: int) -> dict:
        assert token == "token"
        assert (start, end) == (0, 10)
        return {"data": [{"id": 1}]}


def test_incomplete_observed_pagination_never_deactivates_existing_access(monkeypatch) -> None:
    create_sync_run = AsyncMock(return_value=17)
    finish_sync_run = AsyncMock()
    upsert_project_bundle = AsyncMock()
    monkeypatch.setattr(sync_service, "create_sync_run", create_sync_run)
    monkeypatch.setattr(sync_service, "finish_sync_run", finish_sync_run)
    monkeypatch.setattr(sync_service, "upsert_project_bundle", upsert_project_bundle)
    monkeypatch.setattr(sync_service, "normalize_project", lambda row: {"sie_project_id": row["id"]})
    monkeypatch.setattr(sync_service, "normalize_participation", lambda row: {})

    result = asyncio.run(sync_service.synchronize_sie(Pool(), Client(), 10))

    create_sync_run.assert_awaited_once_with(ANY, 10, "sie_api")
    upsert_project_bundle.assert_awaited_once()
    finish_sync_run.assert_awaited_once_with(  # No deactivation call is made for an incomplete run.
        ANY, 17, "success", 1, 1, 1, 1, None
    )
    assert result["is_complete"] is False


def test_failed_sync_persists_a_sanitized_error_summary(monkeypatch) -> None:
    finish_sync_run = AsyncMock()
    monkeypatch.setattr(sync_service, "create_sync_run", AsyncMock(return_value=17))
    monkeypatch.setattr(sync_service, "finish_sync_run", finish_sync_run)

    class FailingClient:
        async def fetch_access_token(self) -> str:
            raise RuntimeError("credential=do-not-persist")

    with pytest.raises(RuntimeError, match="credential=do-not-persist"):
        asyncio.run(sync_service.synchronize_sie(Pool(), FailingClient(), 10))

    error_summary = finish_sync_run.await_args.args[-1]
    assert error_summary == "SIE synchronization failed (RuntimeError)"
    assert "credential" not in error_summary
