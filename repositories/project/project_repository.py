import json
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


def _decode_json_columns(row: asyncpg.Record | dict, defaults: dict[str, object]) -> dict:
    data = dict(row)
    for field_name, default in defaults.items():
        value = data.get(field_name)
        if isinstance(value, str):
            data[field_name] = json.loads(value)
        elif value is None:
            data[field_name] = default
    return data


def _project_contract_columns(include_opportunities: bool = True) -> str:
    opportunities = """
        COALESCE((
          SELECT jsonb_agg(jsonb_build_object(
            'id', opportunity.id,
            'description', opportunity.description,
            'courses', COALESCE((
              SELECT jsonb_agg(jsonb_build_object(
                'id', course.id, 'name', course.name, 'code', course.code,
                'offering_unit', CASE WHEN offering_unit.id IS NULL THEN NULL ELSE jsonb_build_object(
                  'id', offering_unit.id, 'name', offering_unit.name, 'unit_type', offering_unit.unit_type
                ) END
              ) ORDER BY course.name, course.id)
              FROM project_opportunity_courses opportunity_course
              JOIN courses course ON course.id=opportunity_course.course_id
              LEFT JOIN organizational_units offering_unit ON offering_unit.id=course.offering_unit_id
              WHERE opportunity_course.opportunity_id=opportunity.id
            ), '[]'::jsonb)
          ) ORDER BY opportunity.sort_order, opportunity.id)
          FROM project_opportunities opportunity
          WHERE opportunity.project_id=p.id AND opportunity.is_active=TRUE
        ), '[]'::jsonb) AS opportunities,""" if include_opportunities else ""
    return f"""
        p.id, p.sie_project_id, p.process_code, p.title,
        jsonb_build_object(
          'summary', p.source_summary,
          'type', p.source_type,
          'status', p.source_status,
          'starts_at', p.starts_at,
          'ends_at', p.ends_at,
          'center', CASE WHEN center.id IS NULL THEN NULL ELSE jsonb_build_object(
            'id', center.id, 'name', center.name, 'unit_type', center.unit_type
          ) END,
          'executing_unit', CASE WHEN unit.id IS NULL THEN NULL ELSE jsonb_build_object(
            'id', unit.id, 'name', unit.name, 'unit_type', unit.unit_type
          ) END
        ) AS institutional,
        jsonb_build_object(
          'short_description', p.local_short_description,
          'description', p.local_description,
          'areas', COALESCE((
            SELECT jsonb_agg(jsonb_build_object('id', area.id, 'name', area.name, 'slug', area.slug) ORDER BY area.name, area.id)
            FROM project_area_links area_link JOIN project_areas area ON area.id=area_link.area_id
            WHERE area_link.project_id=p.id
          ), '[]'::jsonb),
          'courses', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
              'id', course.id, 'name', course.name, 'code', course.code,
              'offering_unit', CASE WHEN offering_unit.id IS NULL THEN NULL ELSE jsonb_build_object(
                'id', offering_unit.id, 'name', offering_unit.name, 'unit_type', offering_unit.unit_type
              ) END
            ) ORDER BY course.name, course.id)
            FROM project_course_links course_link JOIN courses course ON course.id=course_link.course_id
            LEFT JOIN organizational_units offering_unit ON offering_unit.id=course.offering_unit_id
            WHERE course_link.project_id=p.id
          ), '[]'::jsonb),
          'cover', CASE WHEN cover.id IS NULL THEN NULL ELSE jsonb_build_object(
            'id', cover.id, 'image_url', cover.image_url, 'alt_text', cover.alt_text
          ) END
        ) AS editorial,
        {opportunities}
        p.published_at
    """


async def get_public_projects(
    conn: asyncpg.Connection,
    area_ids: Optional[list[int]],
    centro_ids: Optional[list[int]],
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
    if centro_ids:
        params.append(centro_ids)
        where += f" AND p.center_id=ANY(${len(params)}::BIGINT[])"
    if unidade_ids:
        params.append(unidade_ids)
        where += f" AND p.executing_unit_id=ANY(${len(params)}::BIGINT[])"
    if curso_ids:
        params.append(curso_ids)
        where += f" AND EXISTS (SELECT 1 FROM project_course_links pcl WHERE pcl.project_id=p.id AND pcl.course_id=ANY(${len(params)}::BIGINT[]))"
    total = await conn.fetchval(f"SELECT COUNT(*) FROM projects p WHERE {where}", *params)
    order_by = {
        "titulo_asc": "p.title ASC, p.id ASC",
        "titulo_desc": "p.title DESC, p.id DESC",
        "data_desc": "COALESCE(p.source_updated_on, p.registered_on, p.starts_at, p.published_at::date) DESC NULLS LAST, p.id DESC",
    }.get(ordenacao, "COALESCE(p.source_updated_on, p.registered_on, p.starts_at, p.published_at::date) DESC NULLS LAST, p.id DESC")
    params.extend([page_size, (page - 1) * page_size])
    rows = await conn.fetch(
        f"""
        SELECT {_project_contract_columns()}
        FROM projects p
        LEFT JOIN organizational_units center ON center.id=p.center_id
        LEFT JOIN organizational_units unit ON unit.id=p.executing_unit_id
        LEFT JOIN project_images cover ON cover.project_id=p.id AND cover.image_type='cover'
        WHERE {where}
        ORDER BY {order_by}
        LIMIT ${len(params)-1} OFFSET ${len(params)}
        """,
        *params,
    )
    return [
        _decode_json_columns(
            row,
            {
                "institutional": {},
                "editorial": {},
                "opportunities": [],
            },
        )
        for row in rows
    ], int(total)


async def get_public_project_by_id(conn: asyncpg.Connection, project_id: int) -> dict | None:
    row = await conn.fetchrow(
        f"""
        SELECT {_project_contract_columns()}
        FROM projects p
        LEFT JOIN organizational_units center ON center.id=p.center_id
        LEFT JOIN organizational_units unit ON unit.id=p.executing_unit_id
        LEFT JOIN project_images cover ON cover.project_id=p.id AND cover.image_type='cover'
        WHERE p.id=$1 AND p.is_visible=TRUE AND p.publication_status='published'
        """,
        project_id,
    )
    return _decode_json_columns(
        row,
        {
            "institutional": {},
            "editorial": {},
            "opportunities": [],
        },
    ) if row else None


async def get_user_managed_projects(conn: asyncpg.Connection, user_id: int, user_role: str, page: int, page_size: int, q: Optional[str]) -> tuple[list[dict], int]:
    params: list[object] = []
    if user_role == "admin":
        access = "TRUE"
    else:
        params.append(user_id)
        access = "EXISTS (SELECT 1 FROM project_edit_permissions pep JOIN people person ON person.id=pep.person_id WHERE pep.project_id=p.id AND pep.is_active=TRUE AND person.user_id=$1)"
    query_filter = ""
    if q:
        params.append(q)
        query_filter = f" AND p.title ILIKE ('%' || ${len(params)} || '%')"
    total = await conn.fetchval(f"SELECT COUNT(*) FROM projects p WHERE {access}{query_filter}", *params)
    params.extend([page_size, (page - 1) * page_size])
    rows = await conn.fetch(
        f"""SELECT {_project_contract_columns()}
            FROM projects p
            LEFT JOIN organizational_units center ON center.id=p.center_id
            LEFT JOIN organizational_units unit ON unit.id=p.executing_unit_id
            LEFT JOIN project_images cover ON cover.project_id=p.id AND cover.image_type='cover'
            WHERE {access}{query_filter} ORDER BY p.updated_at DESC, p.id DESC
            LIMIT ${len(params)-1} OFFSET ${len(params)}""",
        *params,
    )
    return [dict(row) for row in rows], int(total)


async def get_user_managed_project_by_id(
    conn: asyncpg.Connection, project_id: int, user_id: int, user_role: str
) -> dict | None:
    if user_role == "admin":
        access = "TRUE"
        params: tuple[object, ...] = (project_id,)
    else:
        access = """EXISTS (
            SELECT 1 FROM project_edit_permissions permission
            JOIN people person ON person.id=permission.person_id
            WHERE permission.project_id=p.id AND person.user_id=$2 AND permission.is_active=TRUE
        )"""
        params = (project_id, user_id)
    row = await conn.fetchrow(
        f"""SELECT {_project_contract_columns()}
            FROM projects p
            LEFT JOIN organizational_units center ON center.id=p.center_id
            LEFT JOIN organizational_units unit ON unit.id=p.executing_unit_id
            LEFT JOIN project_images cover ON cover.project_id=p.id AND cover.image_type='cover'
            WHERE p.id=$1 AND {access}""",
        *params,
    )
    return dict(row) if row else None


async def update_managed_project_fields(conn: asyncpg.Connection, project_id: int, user_id: int, user_role: str, allowed_fields: dict[str, str | None]) -> dict | None:
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
    row = await conn.fetchrow("""WITH previous AS (
          SELECT image_url AS previous_image_url FROM project_images WHERE project_id=$1 AND image_type='cover'
        ), saved AS (
          INSERT INTO project_images(project_id,image_type,image_url,alt_text) VALUES($1,'cover',$2,$3)
          ON CONFLICT (project_id) WHERE image_type='cover' DO UPDATE SET image_url=EXCLUDED.image_url,alt_text=EXCLUDED.alt_text
          RETURNING project_id AS projeto_id,image_url,alt_text
        ) SELECT saved.*, previous.previous_image_url FROM saved LEFT JOIN previous ON TRUE""", project_id, image_url, alt_text)
    return dict(row) if row else None


async def create_project_assignment(conn: asyncpg.Connection, project_id: int, user_id: int, user_role: str, descricao: str, course_ids: list[int]) -> dict:
    if user_role != "admin":
        allowed = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM project_edit_permissions pep JOIN people person ON person.id=pep.person_id WHERE pep.project_id=$1 AND person.user_id=$2 AND pep.is_active=TRUE)", project_id, user_id)
        if not allowed:
            return {"has_project_access": False, "valid_course_count": 0, "requested_course_count": len(course_ids), "assignment": None}
    unique_course_ids = list(dict.fromkeys(course_ids))
    valid_course_count = await conn.fetchval(
        "SELECT COUNT(*) FROM project_course_links WHERE project_id=$1 AND course_id=ANY($2::BIGINT[])",
        project_id, unique_course_ids,
    )
    if valid_course_count != len(unique_course_ids):
        return {"has_project_access": True, "valid_course_count": valid_course_count, "requested_course_count": len(unique_course_ids), "assignment": None}
    row = await conn.fetchrow("INSERT INTO project_opportunities(project_id,description) VALUES($1,$2) RETURNING id,project_id,description", project_id, descricao)
    await conn.executemany("INSERT INTO project_opportunity_courses(opportunity_id,course_id) VALUES($1,$2) ON CONFLICT DO NOTHING", [(row["id"], course_id) for course_id in unique_course_ids])
    courses = await conn.fetch(
        """SELECT course.id, course.name, course.code FROM courses course
           WHERE course.id=ANY($1::BIGINT[]) ORDER BY course.name, course.id""",
        unique_course_ids,
    )
    return {"has_project_access": True, "valid_course_count": valid_course_count, "requested_course_count": len(unique_course_ids), "assignment": {"id": row["id"], "project_id": row["project_id"], "description": row["description"], "courses": [dict(course) for course in courses]}}


async def deactivate_project_assignment(conn: asyncpg.Connection, assignment_id: int, user_id: int, user_role: str) -> bool:
    row = await conn.fetchrow("""SELECT po.project_id FROM project_opportunities po WHERE po.id=$1 AND po.is_active=TRUE""", assignment_id)
    if not row:
        return False
    if user_role != "admin":
        allowed = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM project_edit_permissions pep JOIN people person ON person.id=pep.person_id WHERE pep.project_id=$1 AND person.user_id=$2 AND pep.is_active=TRUE)", row["project_id"], user_id)
        if not allowed:
            return False
    return bool(await conn.fetchval("UPDATE project_opportunities SET is_active=FALSE,updated_at=NOW() WHERE id=$1 RETURNING id", assignment_id))
