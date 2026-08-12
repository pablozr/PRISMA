import asyncpg


async def get_dashboard_metrics_row(conn: asyncpg.Connection) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT
          (SELECT COUNT(*)::BIGINT FROM projects) AS total_projects,
          (SELECT COUNT(*)::BIGINT FROM projects WHERE is_visible=FALSE) AS inactive_projects,
          (SELECT COUNT(*)::BIGINT FROM users) AS total_users,
          (SELECT COUNT(*)::BIGINT FROM users WHERE is_active=TRUE) AS active_users;
        """
    )
    return dict(row) if row else None


def _project_search_clause() -> str:
    return """NULLIF(TRIM($1::TEXT), '') IS NULL
        OR p.title ILIKE ('%' || TRIM($1::TEXT) || '%')
        OR COALESCE(p.local_short_description, p.source_summary, '') ILIKE ('%' || TRIM($1::TEXT) || '%')"""


async def count_admin_projects(conn: asyncpg.Connection, q: str | None) -> int:
    row = await conn.fetchrow(
        f"""SELECT COUNT(*)::BIGINT AS total FROM projects p
            WHERE {_project_search_clause()};""",
        q,
    )
    return int(row["total"]) if row else 0


async def list_admin_projects_paginated(
    conn: asyncpg.Connection, q: str | None, page_size: int, offset: int
) -> list[dict]:
    rows = await conn.fetch(
        f"""
        SELECT p.id, p.sie_project_id, p.process_code, p.title,
               p.source_status, p.source_type,
               p.publication_status, p.is_visible, p.updated_at, p.published_at,
               COALESCE(managers.managers, '[]'::jsonb) AS managers
        FROM projects p
        LEFT JOIN LATERAL (
          SELECT jsonb_agg(jsonb_build_object(
            'person_id', person.id,
            'user_id', person.user_id,
            'profile', person.profile,
            'permission_source', permission.permission_source
          ) ORDER BY CASE permission.permission_source WHEN 'coordinator' THEN 0 ELSE 1 END, person.id) AS managers
          FROM project_edit_permissions permission
          JOIN people person ON person.id=permission.person_id
          WHERE permission.project_id=p.id AND permission.is_active=TRUE
        ) managers ON TRUE
        WHERE {_project_search_clause()}
        ORDER BY p.updated_at DESC, p.id DESC LIMIT $2 OFFSET $3;
        """,
        q, page_size, offset,
    )
    return [dict(row) for row in rows]


async def update_admin_project_fields(
    conn: asyncpg.Connection, project_id: int, publication_status: str | None, is_visible: bool | None
) -> dict | None:
    updates: list[str] = []
    params: list[object] = [project_id, publication_status, is_visible]
    if publication_status is not None:
        updates.append("publication_status=$2")
    if is_visible is not None:
        updates.append("is_visible=$3")
    if not updates:
        return None
    updates.append("""published_at=CASE
        WHEN COALESCE($2, publication_status)='published' AND COALESCE($3, is_visible)=TRUE
          THEN COALESCE(published_at, NOW())
        ELSE NULL
    END""")
    updates.append("updated_at=NOW()")
    row = await conn.fetchrow(
        f"""UPDATE projects SET {', '.join(updates)} WHERE id=$1
            RETURNING id, process_code, title,
               source_status, source_type, publication_status, is_visible, updated_at, published_at;""",
        *params,
    )
    return dict(row) if row else None


async def count_sync_runs(conn: asyncpg.Connection) -> int:
    return int(await conn.fetchval("SELECT COUNT(*) FROM sync_runs"))


async def list_sync_runs_paginated(conn: asyncpg.Connection, page_size: int, offset: int) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id, source, status, is_complete, started_at, finished_at, page_size,
                  pages_processed, rows_received, projects_upserted, participants_upserted,
                  error_summary
           FROM sync_runs ORDER BY started_at DESC, id DESC LIMIT $1 OFFSET $2""",
        page_size, offset,
    )
    return [dict(row) for row in rows]


async def count_sync_run_failures(conn: asyncpg.Connection, sync_run_id: int) -> int:
    return int(await conn.fetchval(
        "SELECT COUNT(*) FROM sync_runs WHERE id=$1 AND error_summary IS NOT NULL", sync_run_id
    ))


async def list_sync_run_failures_paginated(
    conn: asyncpg.Connection, sync_run_id: int, page_size: int, offset: int
) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id AS sync_run_id, error_summary, finished_at
           FROM sync_runs WHERE id=$1 AND error_summary IS NOT NULL LIMIT $2 OFFSET $3""",
        sync_run_id, page_size, offset,
    )
    return [dict(row) for row in rows]
