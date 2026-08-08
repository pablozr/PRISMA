from typing import Optional

import asyncpg


def _public_where(query: Optional[str], params: list[object]) -> str:
    clauses = ["p.is_visible = TRUE", "p.publication_status = 'published'"]
    if query:
        params.append(query)
        placeholder = f"${len(params)}"
        clauses.append(
            f"(p.title ILIKE ('%' || {placeholder} || '%') OR "
            f"COALESCE(p.local_short_description, p.source_summary, '') ILIKE ('%' || {placeholder} || '%'))"
        )
    return " AND ".join(clauses)


async def get_public_projects(
    conn: asyncpg.Connection,
    area_ids: Optional[list[int]],
    unidade_ids: Optional[list[int]],
    curso_ids: Optional[list[int]],
    ordenacao: str,
    page: int,
    page_size: int,
    somente_habilitados: bool,
    q: Optional[str],
) -> tuple[list[dict], int]:
    params: list[object] = []
    where = _public_where(q, params)
    if area_ids:
        params.append(area_ids)
        where += f" AND EXISTS (SELECT 1 FROM project_area_links pal WHERE pal.project_id=p.id AND pal.area_id=ANY(${len(params)}::BIGINT[]))"
    if unidade_ids:
        params.append(unidade_ids)
        where += f" AND (p.center_id=ANY(${len(params)}::BIGINT[]) OR p.executing_unit_id=ANY(${len(params)}::BIGINT[]))"
    if curso_ids:
        params.append(curso_ids)
        where += f" AND EXISTS (SELECT 1 FROM project_course_links pcl WHERE pcl.project_id=p.id AND pcl.course_id=ANY(${len(params)}::BIGINT[]))"
    total = await conn.fetchval(f"SELECT COUNT(*) FROM projects p WHERE {where}", *params)
    params.extend([page_size, (page - 1) * page_size])
    rows = await conn.fetch(
        f"""
        SELECT p.id, p.sie_project_id, p.process_code, p.title,
               COALESCE(p.local_short_description, p.source_summary) AS short_description,
               p.local_description AS full_description, p.source_type AS project_type_name,
               p.source_status, p.starts_at, p.ends_at, p.published_at,
               unit.id AS executing_unit_id, unit.name AS executing_unit_name,
               cover.image_url AS cover_image_url, cover.alt_text AS cover_image_alt_text
        FROM projects p
        LEFT JOIN organizational_units unit ON unit.id=p.executing_unit_id
        LEFT JOIN project_images cover ON cover.project_id=p.id AND cover.image_type='cover'
        WHERE {where}
        ORDER BY p.published_at DESC NULLS LAST, p.id DESC
        LIMIT ${len(params)-1} OFFSET ${len(params)}
        """,
        *params,
    )
    return [dict(row) for row in rows], int(total)


async def get_public_project_by_id(conn: asyncpg.Connection, project_id: int) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT p.id, p.sie_project_id, p.process_code, p.title, p.source_summary,
               p.local_short_description AS short_description, p.local_description AS full_description,
               p.source_type AS project_type_name, p.source_status, p.starts_at, p.ends_at, p.published_at
        FROM projects p
        WHERE p.id=$1 AND p.is_visible=TRUE AND p.publication_status='published'
        """,
        project_id,
    )
    return dict(row) if row else None


async def exists_public_project(conn: asyncpg.Connection, project_id: int) -> bool:
    return bool(await conn.fetchval("SELECT EXISTS(SELECT 1 FROM projects WHERE id=$1 AND is_visible=TRUE AND publication_status='published')", project_id))


async def get_public_project_assignments(conn: asyncpg.Connection, project_id: int) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id AS atribuicao_id, project_id AS projeto_id, description AS descricao
           FROM project_opportunities WHERE project_id=$1 AND is_active=TRUE ORDER BY sort_order, id""",
        project_id,
    )
    return [dict(row) for row in rows]


async def get_user_managed_projects(conn: asyncpg.Connection, user_id: int, user_role: str, page: int, page_size: int, q: Optional[str]) -> tuple[list[dict], int]:
    params: list[object] = [user_id]
    access = "TRUE" if user_role == "admin" else "EXISTS (SELECT 1 FROM project_edit_permissions pep JOIN people person ON person.id=pep.person_id WHERE pep.project_id=p.id AND pep.is_active=TRUE AND person.user_id=$1)"
    query_filter = ""
    if q:
        params.append(q)
        query_filter = f" AND p.title ILIKE ('%' || ${len(params)} || '%')"
    total = await conn.fetchval(f"SELECT COUNT(*) FROM projects p WHERE {access}{query_filter}", *params)
    params.extend([page_size, (page - 1) * page_size])
    rows = await conn.fetch(
        f"SELECT p.id, p.title, p.local_short_description AS short_description, p.local_description AS full_description, p.updated_at FROM projects p WHERE {access}{query_filter} ORDER BY p.updated_at DESC LIMIT ${len(params)-1} OFFSET ${len(params)}",
        *params,
    )
    return [dict(row) for row in rows], int(total)


async def update_managed_project_fields(conn: asyncpg.Connection, project_id: int, user_id: int, user_role: str, allowed_fields: dict[str, str]) -> dict | None:
    column_map = {"local_short_description": "local_short_description", "local_description": "local_description"}
    fields = [(column_map[name], value) for name, value in allowed_fields.items() if name in column_map]
    if not fields:
        return None
    if user_role != "admin":
        allowed = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM project_edit_permissions pep JOIN people person ON person.id=pep.person_id WHERE pep.project_id=$1 AND person.user_id=$2 AND pep.is_active=TRUE)", project_id, user_id)
        if not allowed:
            return None
    params: list[object] = [project_id]
    assignments = []
    for name, value in fields:
        params.append(value)
        assignments.append(f"{name}=${len(params)}")
    row = await conn.fetchrow(f"UPDATE projects SET {', '.join(assignments)}, updated_at=NOW() WHERE id=$1 RETURNING id, title, local_short_description AS short_description, local_description AS full_description", *params)
    return dict(row) if row else None


async def upsert_project_cover_image(conn: asyncpg.Connection, project_id: int, user_id: int, user_role: str, image_url: str, alt_text: Optional[str]) -> dict | None:
    if user_role != "admin":
        allowed = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM project_edit_permissions pep JOIN people person ON person.id=pep.person_id WHERE pep.project_id=$1 AND person.user_id=$2 AND pep.is_active=TRUE)", project_id, user_id)
        if not allowed:
            return None
    row = await conn.fetchrow("""INSERT INTO project_images(project_id,image_type,image_url,alt_text) VALUES($1,'cover',$2,$3)
        ON CONFLICT (project_id) WHERE image_type='cover' DO UPDATE SET image_url=EXCLUDED.image_url,alt_text=EXCLUDED.alt_text
        RETURNING project_id AS projeto_id,image_url,alt_text""", project_id, image_url, alt_text)
    return dict(row) if row else None


async def create_project_assignment(conn: asyncpg.Connection, project_id: int, user_id: int, user_role: str, descricao: str, course_ids: list[int]) -> dict:
    if user_role != "admin":
        allowed = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM project_edit_permissions pep JOIN people person ON person.id=pep.person_id WHERE pep.project_id=$1 AND person.user_id=$2 AND pep.is_active=TRUE)", project_id, user_id)
        if not allowed:
            return {"has_project_access": False, "valid_course_count": 0, "requested_course_count": len(course_ids), "assignment": None}
    row = await conn.fetchrow("INSERT INTO project_opportunities(project_id,description) VALUES($1,$2) RETURNING id,project_id,description", project_id, descricao)
    await conn.executemany("INSERT INTO project_opportunity_courses(opportunity_id,course_id) VALUES($1,$2) ON CONFLICT DO NOTHING", [(row["id"], course_id) for course_id in course_ids])
    return {"has_project_access": True, "valid_course_count": len(course_ids), "requested_course_count": len(course_ids), "assignment": {"atribuicao_id": row["id"], "projeto_id": row["project_id"], "descricao": row["description"], "curso_ids": course_ids}}


async def deactivate_project_assignment(conn: asyncpg.Connection, assignment_id: int, user_id: int, user_role: str) -> bool:
    row = await conn.fetchrow("""SELECT po.project_id FROM project_opportunities po WHERE po.id=$1 AND po.is_active=TRUE""", assignment_id)
    if not row:
        return False
    if user_role != "admin":
        allowed = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM project_edit_permissions pep JOIN people person ON person.id=pep.person_id WHERE pep.project_id=$1 AND person.user_id=$2 AND pep.is_active=TRUE)", row["project_id"], user_id)
        if not allowed:
            return False
    return bool(await conn.fetchval("UPDATE project_opportunities SET is_active=FALSE,updated_at=NOW() WHERE id=$1 RETURNING id", assignment_id))
