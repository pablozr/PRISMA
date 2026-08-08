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
        OR COALESCE(p.local_short_description, p.source_summary, '') ILIKE ('%' || TRIM($1::TEXT) || '%')
        OR COALESCE(coordinator.full_name, '') ILIKE ('%' || TRIM($1::TEXT) || '%')
        OR COALESCE(coordinator.institutional_email::TEXT, '') ILIKE ('%' || TRIM($1::TEXT) || '%')"""


async def count_admin_projects(conn: asyncpg.Connection, q: str | None) -> int:
    row = await conn.fetchrow(
        f"""SELECT COUNT(*)::BIGINT AS total FROM projects p
            LEFT JOIN LATERAL (
              SELECT person.full_name, person.institutional_email
              FROM project_edit_permissions permission JOIN people person ON person.id=permission.person_id
              WHERE permission.project_id=p.id AND permission.is_active=TRUE
              ORDER BY CASE permission.permission_source WHEN 'coordinator' THEN 0 ELSE 1 END, person.id LIMIT 1
            ) coordinator ON TRUE
            WHERE {_project_search_clause()};""",
        q,
    )
    return int(row["total"]) if row else 0


async def list_admin_projects_paginated(
    conn: asyncpg.Connection, q: str | None, page_size: int, offset: int
) -> list[dict]:
    rows = await conn.fetch(
        f"""
        SELECT p.id, p.process_code, p.title,
               COALESCE(p.local_short_description, p.source_summary) AS short_description,
               p.publication_status AS status, p.is_visible AS is_active,
               p.updated_at, p.published_at,
               coordinator.user_id AS responsible_id, coordinator.full_name AS responsible_name,
               coordinator.institutional_email::TEXT AS responsible_email,
               CASE WHEN coordinator.profile='tecnico' THEN 'tecnico' ELSE 'docente' END AS responsible_type
        FROM projects p
        LEFT JOIN LATERAL (
          SELECT person.user_id, person.full_name, person.institutional_email, person.profile
          FROM project_edit_permissions permission
          JOIN people person ON person.id=permission.person_id
          WHERE permission.project_id=p.id AND permission.is_active=TRUE
          ORDER BY CASE permission.permission_source WHEN 'coordinator' THEN 0 ELSE 1 END, person.id
          LIMIT 1
        ) coordinator ON TRUE
        WHERE {_project_search_clause()}
        ORDER BY p.updated_at DESC, p.id DESC LIMIT $2 OFFSET $3;
        """,
        q, page_size, offset,
    )
    return [dict(row) for row in rows]


async def update_admin_project_fields(
    conn: asyncpg.Connection, project_id: int, status: str | None, is_active: bool | None
) -> dict | None:
    updates: list[str] = []
    params: list[object] = [project_id]
    if status is not None:
        params.append(status)
        updates.append(f"publication_status=${len(params)}")
    if is_active is not None:
        params.append(is_active)
        updates.append(f"is_visible=${len(params)}")
    if not updates:
        return None
    updates.append("published_at=CASE WHEN is_visible=TRUE AND publication_status='published' THEN COALESCE(published_at, NOW()) ELSE published_at END")
    updates.append("updated_at=NOW()")
    row = await conn.fetchrow(
        f"""UPDATE projects SET {', '.join(updates)} WHERE id=$1
            RETURNING id, process_code, title,
              COALESCE(local_short_description, source_summary) AS short_description,
              publication_status AS status, is_visible AS is_active, updated_at, published_at;""",
        *params,
    )
    return dict(row) if row else None


async def count_import_batches(conn: asyncpg.Connection) -> int:
    return int(await conn.fetchval("SELECT COUNT(*) FROM sync_runs"))


async def list_import_batches_paginated(conn: asyncpg.Connection, page_size: int, offset: int) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id, 'SIE API' AS source_filename, status, rows_received AS total_rows,
                  participants_upserted AS imported_rows, 0::BIGINT AS rejected_rows,
                  started_at AS created_at, finished_at
           FROM sync_runs ORDER BY started_at DESC, id DESC LIMIT $1 OFFSET $2""",
        page_size, offset,
    )
    return [dict(row) for row in rows]


async def count_import_errors_by_batch(conn: asyncpg.Connection, batch_id: int) -> int:
    return int(await conn.fetchval(
        "SELECT COUNT(*) FROM sync_runs WHERE id=$1 AND error_summary IS NOT NULL", batch_id
    ))


async def list_import_errors_by_batch_paginated(
    conn: asyncpg.Connection, batch_id: int, page_size: int, offset: int
) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id, id AS import_batch_id, 0::INTEGER AS row_number,
                  NULL::JSONB AS raw_payload, error_summary AS error_reason, finished_at AS created_at
           FROM sync_runs WHERE id=$1 AND error_summary IS NOT NULL LIMIT $2 OFFSET $3""",
        batch_id, page_size, offset,
    )
    return [dict(row) for row in rows]
