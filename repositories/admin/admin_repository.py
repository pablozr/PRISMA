import asyncpg


async def get_dashboard_metrics_row(conn: asyncpg.Connection) -> dict | None:
    query = """
            SELECT
                (SELECT COUNT(*)::BIGINT FROM projects) AS total_projects,
                (SELECT COUNT(*)::BIGINT FROM projects WHERE is_active = FALSE) AS inactive_projects,
                (SELECT COUNT(*)::BIGINT FROM users) AS total_users,
                (SELECT COUNT(*)::BIGINT FROM users WHERE is_active = TRUE) AS active_users;
            """

    row = await conn.fetchrow(query)
    return {**row} if row else None


async def count_admin_projects(conn: asyncpg.Connection, q: str | None) -> int:
    query = """
            SELECT COUNT(*)::BIGINT AS total
            FROM projects p
            LEFT JOIN users ru ON ru.id = p.responsible_user_id
            WHERE NULLIF(TRIM($1::TEXT), '') IS NULL
               OR p.title ILIKE ('%' || TRIM($1::TEXT) || '%')
               OR COALESCE(p.short_description, '') ILIKE ('%' || TRIM($1::TEXT) || '%')
               OR COALESCE(ru.full_name, '') ILIKE ('%' || TRIM($1::TEXT) || '%')
               OR COALESCE(ru.institutional_email::TEXT, '') ILIKE ('%' || TRIM($1::TEXT) || '%');
            """

    row = await conn.fetchrow(query, q)
    return int(row["total"]) if row else 0


async def list_admin_projects_paginated(
    conn: asyncpg.Connection,
    q: str | None,
    page_size: int,
    offset: int,
) -> list[dict]:
    query = """
            SELECT
                p.id,
                p.process_code,
                p.title,
                p.short_description,
                p.status,
                p.is_active,
                p.updated_at,
                p.published_at,
                p.responsible_user_id AS responsible_id,
                ru.full_name AS responsible_name,
                ru.institutional_email::TEXT AS responsible_email,
                CASE
                    WHEN ru.role = 'tecnico' THEN 'tecnico'
                    ELSE 'docente'
                END AS responsible_type
            FROM projects p
            LEFT JOIN users ru ON ru.id = p.responsible_user_id
            WHERE NULLIF(TRIM($1::TEXT), '') IS NULL
               OR p.title ILIKE ('%' || TRIM($1::TEXT) || '%')
               OR COALESCE(p.short_description, '') ILIKE ('%' || TRIM($1::TEXT) || '%')
               OR COALESCE(ru.full_name, '') ILIKE ('%' || TRIM($1::TEXT) || '%')
               OR COALESCE(ru.institutional_email::TEXT, '') ILIKE ('%' || TRIM($1::TEXT) || '%')
            ORDER BY p.updated_at DESC, p.id DESC
            LIMIT $2
            OFFSET $3;
            """

    rows = await conn.fetch(query, q, page_size, offset)
    return [{**row} for row in rows]


async def update_admin_project_fields(
    conn: asyncpg.Connection,
    project_id: int,
    status: str | None,
    is_active: bool | None,
) -> dict | None:
    updates: list[str] = []
    params: list[object] = [project_id]

    if status is not None:
        params.append(status)
        updates.append(f"status = ${len(params)}")

    if is_active is not None:
        params.append(is_active)
        updates.append(f"is_active = ${len(params)}")
        if is_active:
            updates.append("deactivated_at = NULL")
        else:
            updates.append("deactivated_at = NOW()")

    if not updates:
        return None

    updates.append("updated_at = NOW()")
    query = f"""
            UPDATE projects p
            SET {', '.join(updates)}
            WHERE p.id = $1
            RETURNING
                p.id,
                p.process_code,
                p.title,
                p.short_description,
                p.status,
                p.is_active,
                p.updated_at,
                p.published_at,
                p.responsible_user_id AS responsible_id;
            """

    row = await conn.fetchrow(query, *params)
    return {**row} if row else None


async def create_import_batch_row(
    conn: asyncpg.Connection,
    reference_year: int,
    reference_term: int,
    uploaded_by_user_id: int,
    filename: str,
    source_hash: str,
    total_rows: int,
) -> dict | None:
    query = """
            INSERT INTO import_batches (
                reference_year,
                reference_term,
                uploaded_by_user_id,
                source_filename,
                source_hash,
                status,
                total_rows,
                imported_rows,
                rejected_rows,
                created_at,
                finished_at
            )
            VALUES ($1, $2, $3, $4, $5, 'success', $6, $6, 0, NOW(), NOW())
            RETURNING id, status, total_rows, imported_rows, rejected_rows, created_at, finished_at;
            """

    row = await conn.fetchrow(
        query,
        reference_year,
        reference_term,
        uploaded_by_user_id,
        filename,
        source_hash,
        total_rows,
    )
    return {**row} if row else None


async def count_import_batches(conn: asyncpg.Connection) -> int:
    row = await conn.fetchrow("SELECT COUNT(*)::BIGINT AS total FROM import_batches;")
    return int(row["total"]) if row else 0


async def list_import_batches_paginated(conn: asyncpg.Connection, page_size: int, offset: int) -> list[dict]:
    query = """
            SELECT
                ib.id,
                ib.reference_year,
                ib.reference_term,
                ib.source_filename,
                ib.source_hash,
                ib.status,
                ib.total_rows,
                ib.imported_rows,
                ib.rejected_rows,
                ib.created_at,
                ib.finished_at,
                u.id AS uploaded_by_user_id,
                u.full_name AS uploaded_by_name,
                u.institutional_email::TEXT AS uploaded_by_email
            FROM import_batches ib
            LEFT JOIN users u ON u.id = ib.uploaded_by_user_id
            ORDER BY ib.created_at DESC, ib.id DESC
            LIMIT $1
            OFFSET $2;
            """

    rows = await conn.fetch(query, page_size, offset)
    return [{**row} for row in rows]


async def count_import_errors_by_batch(conn: asyncpg.Connection, batch_id: int) -> int:
    query = "SELECT COUNT(*)::BIGINT AS total FROM import_row_errors WHERE import_batch_id = $1;"
    row = await conn.fetchrow(query, batch_id)
    return int(row["total"]) if row else 0


async def list_import_errors_by_batch_paginated(
    conn: asyncpg.Connection,
    batch_id: int,
    page_size: int,
    offset: int,
) -> list[dict]:
    query = """
            SELECT id, import_batch_id, row_number, raw_payload, error_reason, created_at
            FROM import_row_errors
            WHERE import_batch_id = $1
            ORDER BY row_number ASC, id ASC
            LIMIT $2
            OFFSET $3;
            """

    rows = await conn.fetch(query, batch_id, page_size, offset)
    return [{**row} for row in rows]
