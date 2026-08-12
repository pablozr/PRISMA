import asyncio
from unittest.mock import AsyncMock

from repositories.admin import admin_repository
from repositories.sie import sie_repository


def test_admin_project_queries_use_catalogue_schema() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"total": 0})
    conn.fetch = AsyncMock(return_value=[])

    asyncio.run(admin_repository.count_admin_projects(conn, "teste"))
    asyncio.run(admin_repository.list_admin_projects_paginated(conn, "teste", 20, 0))
    asyncio.run(admin_repository.update_admin_project_fields(conn, 1, "published", True))

    queries = "\n".join(call.args[0] for call in [*conn.fetchrow.await_args_list, *conn.fetch.await_args_list])
    assert "publication_status" in queries
    assert "is_visible" in queries
    assert "responsible_user_id" not in queries
    assert "p.short_description" not in queries
    assert "managers" in queries
    assert "responsible_email" not in queries
    assert "COALESCE($2, publication_status)='published'" in queries


def test_admin_project_publication_timestamp_uses_requested_values() -> None:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    asyncio.run(admin_repository.update_admin_project_fields(conn, 1, "published", None))
    asyncio.run(admin_repository.update_admin_project_fields(conn, 1, None, False))
    asyncio.run(admin_repository.update_admin_project_fields(conn, 1, "draft", True))

    calls = conn.fetchrow.await_args_list
    for call in calls:
        query = call.args[0]
        assert "COALESCE($2, publication_status)='published'" in query
        assert "COALESCE($3, is_visible)=TRUE" in query
        assert "ELSE NULL" in query

    assert calls[0].args[1:] == (1, "published", None)
    assert calls[1].args[1:] == (1, None, False)
    assert calls[2].args[1:] == (1, "draft", True)


def test_admin_sync_run_history_uses_explicit_sync_contract() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)
    conn.fetch = AsyncMock(return_value=[])

    asyncio.run(admin_repository.count_sync_runs(conn))
    asyncio.run(admin_repository.list_sync_runs_paginated(conn, 20, 0))
    asyncio.run(admin_repository.count_sync_run_failures(conn, 1))
    asyncio.run(admin_repository.list_sync_run_failures_paginated(conn, 1, 20, 0))

    queries = "\n".join(
        call.args[0] for call in [*conn.fetchval.await_args_list, *conn.fetch.await_args_list]
    )
    assert "sync_runs" in queries
    assert "import_batches" not in queries
    assert "import_row_errors" not in queries
    assert "source" in queries
    assert "is_complete" in queries
    assert "raw_payload" not in queries


def test_sync_run_repository_persists_source_and_incomplete_status() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=7)

    asyncio.run(sie_repository.create_sync_run(conn, 20, "sie_api"))
    asyncio.run(sie_repository.finish_sync_run(conn, 7, "success", 2, 20, 4, 20))

    insert_query = conn.fetchval.await_args.args[0]
    finish_query = conn.execute.await_args.args[0]
    assert "source" in insert_query
    assert conn.fetchval.await_args.args[1:] == ("sie_api", 20)
    assert "is_complete" in finish_query
    assert conn.execute.await_args.args[-1] is False
