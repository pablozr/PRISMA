import asyncio
from unittest.mock import AsyncMock

from repositories.admin import admin_repository


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


def test_admin_import_history_reads_sync_runs() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)
    conn.fetch = AsyncMock(return_value=[])

    asyncio.run(admin_repository.count_import_batches(conn))
    asyncio.run(admin_repository.list_import_batches_paginated(conn, 20, 0))
    asyncio.run(admin_repository.count_import_errors_by_batch(conn, 1))
    asyncio.run(admin_repository.list_import_errors_by_batch_paginated(conn, 1, 20, 0))

    queries = "\n".join(
        call.args[0] for call in [*conn.fetchval.await_args_list, *conn.fetch.await_args_list]
    )
    assert "sync_runs" in queries
    assert "import_batches" not in queries
    assert "import_row_errors" not in queries
