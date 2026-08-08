import asyncpg


async def list_public_projects(
    conn: asyncpg.Connection,
    page: int,
    page_size: int,
    query: str | None = None,
) -> tuple[list[dict], int]:
    where = "p.is_visible = TRUE AND p.publication_status = 'published'"
    params: list[object] = []
    if query:
        params.append(query)
        where += f" AND (p.title ILIKE ('%' || ${len(params)} || '%') OR COALESCE(p.local_short_description, p.source_summary, '') ILIKE ('%' || ${len(params)} || '%'))"
    total = await conn.fetchval(f"SELECT COUNT(*) FROM projects p WHERE {where};", *params)
    params.extend([page_size, (page - 1) * page_size])
    rows = await conn.fetch(
        f"""
        SELECT p.id, p.sie_project_id, p.process_code, p.title, p.source_summary,
               p.local_short_description, p.local_description, p.source_type, p.source_status,
               p.starts_at, p.ends_at, p.published_at
        FROM projects p WHERE {where}
        ORDER BY p.published_at DESC NULLS LAST, p.id DESC
        LIMIT ${len(params) - 1} OFFSET ${len(params)};
        """,
        *params,
    )
    return [dict(row) for row in rows], int(total)
