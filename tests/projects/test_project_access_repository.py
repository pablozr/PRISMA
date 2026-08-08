import asyncio
from unittest.mock import AsyncMock

from repositories.project.project_access_repository import can_edit_project


def test_admin_can_edit_without_database_query():
    conn = object()
    assert asyncio.run(can_edit_project(conn, 1, 1, "admin")) is True


def test_permission_uses_imported_person_link():
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=True)
    assert asyncio.run(can_edit_project(conn, 3, 4, "professor")) is True
    conn.fetchval.assert_awaited_once()
