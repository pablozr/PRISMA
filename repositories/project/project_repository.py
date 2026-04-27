from typing import Literal, Optional

import asyncpg

from core.config.config import (
    PROJECTS_SORT_DATA_DESC,
    PROJECTS_SORT_TITULO_ASC,
    PROJECTS_SORT_TITULO_DESC,
)

ProjectSortOption = Literal[
    PROJECTS_SORT_TITULO_ASC,
    PROJECTS_SORT_TITULO_DESC,
    PROJECTS_SORT_DATA_DESC,
]

ORDER_BY_MAP: dict[ProjectSortOption, str] = {
    PROJECTS_SORT_TITULO_ASC: "p.title ASC, p.id ASC",
    PROJECTS_SORT_TITULO_DESC: "p.title DESC, p.id DESC",
    PROJECTS_SORT_DATA_DESC: "COALESCE(p.published_at, p.created_at) DESC, p.id DESC",
}

MANAGED_PROJECT_UPDATE_COLUMNS = {
    "title",
    "full_description",
}


def _build_projects_where_clause(
    area_ids: Optional[list[int]],
    unidade_ids: Optional[list[int]],
    curso_ids: Optional[list[int]],
    somente_habilitados: bool,
    q: Optional[str],
) -> tuple[str, list[object]]:
    clauses = [
        "p.is_active = TRUE",
        "p.status = 'published'",
    ]
    params: list[object] = []

    if somente_habilitados:
        clauses.append("COALESCE(pt.is_enabled, TRUE) = TRUE")

    if area_ids:
        area_ids_placeholder = f"${len(params) + 1}"
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM project_area_links pal
                WHERE pal.project_id = p.id
                  AND pal.area_id = ANY({area_ids_placeholder}::BIGINT[])
            )
            """
        )
        params.append(area_ids)

    if unidade_ids:
        unidade_ids_placeholder = f"${len(params) + 1}"
        clauses.append(
            f"""
            (
                p.executing_unit_id = ANY({unidade_ids_placeholder}::BIGINT[])
                OR EXISTS (
                    SELECT 1
                    FROM project_course_links pcl
                    JOIN courses c ON c.id = pcl.course_id
                    WHERE pcl.project_id = p.id
                      AND c.unit_id = ANY({unidade_ids_placeholder}::BIGINT[])
                )
            )
            """
        )
        params.append(unidade_ids)

    if curso_ids:
        curso_ids_placeholder = f"${len(params) + 1}"
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM project_course_links pcl
                WHERE pcl.project_id = p.id
                  AND pcl.course_id = ANY({curso_ids_placeholder}::BIGINT[])
            )
            """
        )
        params.append(curso_ids)

    normalized_q = (q or "").strip()
    if normalized_q:
        q_placeholder = f"${len(params) + 1}"
        clauses.append(
            f"""
            (
                p.title ILIKE {q_placeholder}
                OR COALESCE(p.short_description, '') ILIKE {q_placeholder}
                OR COALESCE(p.full_description, '') ILIKE {q_placeholder}
            )
            """
        )
        params.append(f"%{normalized_q}%")

    return "\n      AND ".join(clauses), params


async def get_public_projects(
    conn: asyncpg.Connection,
    area_ids: Optional[list[int]],
    unidade_ids: Optional[list[int]],
    curso_ids: Optional[list[int]],
    ordenacao: ProjectSortOption,
    page: int,
    page_size: int,
    somente_habilitados: bool,
    q: Optional[str],
) -> tuple[list[dict], int]:
    where_clause, params = _build_projects_where_clause(
        area_ids=area_ids,
        unidade_ids=unidade_ids,
        curso_ids=curso_ids,
        somente_habilitados=somente_habilitados,
        q=q,
    )

    count_query = f"""
        SELECT COUNT(*)::BIGINT AS total
        FROM projects p
        LEFT JOIN project_types pt ON pt.id = p.project_type_id
        WHERE {where_clause};
    """

    count_row = await conn.fetchrow(count_query, *params)
    total = int(count_row["total"]) if count_row else 0

    offset = (page - 1) * page_size
    limit_placeholder = f"${len(params) + 1}"
    offset_placeholder = f"${len(params) + 2}"
    order_by_clause = ORDER_BY_MAP[ordenacao]

    query = f"""
        SELECT
            p.id,
            p.process_code,
            p.title,
            p.short_description,
            p.full_description,
            p.contact_email,
            p.owner_professor_id,
            pr.full_name AS owner_professor_name,
            p.executing_unit_id,
            ou.name AS executing_unit_name,
            ou.short_name AS executing_unit_short_name,
            ou.type AS executing_unit_type,
            p.source_import_batch_id,
            p.project_type_id,
            pt.name AS project_type_name,
            pt.slug AS project_type_slug,
            COALESCE(pt.is_enabled, TRUE) AS project_type_is_enabled,
            p.status,
            p.is_active,
            p.starts_at,
            p.ends_at,
            p.created_at,
            p.updated_at,
            p.published_at,
            p.deactivated_at,
            COALESCE(
                ARRAY(
                    SELECT pal.area_id
                    FROM project_area_links pal
                    WHERE pal.project_id = p.id
                    ORDER BY pal.area_id
                ),
                ARRAY[]::BIGINT[]
            ) AS area_ids,
            COALESCE(
                ARRAY(
                    SELECT pcl.course_id
                    FROM project_course_links pcl
                    WHERE pcl.project_id = p.id
                    ORDER BY pcl.course_id
                ),
                ARRAY[]::BIGINT[]
            ) AS course_ids
        FROM projects p
        LEFT JOIN professor_registry pr ON pr.id = p.owner_professor_id
        LEFT JOIN organizational_units ou ON ou.id = p.executing_unit_id
        LEFT JOIN project_types pt ON pt.id = p.project_type_id
        WHERE {where_clause}
        ORDER BY {order_by_clause}
        LIMIT {limit_placeholder}
        OFFSET {offset_placeholder};
    """

    rows = await conn.fetch(query, *params, page_size, offset)
    return [{**row} for row in rows], total


async def get_public_project_by_id(conn: asyncpg.Connection, project_id: int) -> dict | None:
    query = """
        SELECT
            p.id,
            p.process_code,
            p.title,
            p.short_description,
            p.full_description,
            p.contact_email,
            p.owner_professor_id,
            pr.full_name AS owner_professor_name,
            p.executing_unit_id,
            ou.name AS executing_unit_name,
            ou.short_name AS executing_unit_short_name,
            ou.type AS executing_unit_type,
            p.source_import_batch_id,
            p.project_type_id,
            pt.name AS project_type_name,
            pt.slug AS project_type_slug,
            COALESCE(pt.is_enabled, TRUE) AS project_type_is_enabled,
            p.status,
            p.is_active,
            p.starts_at,
            p.ends_at,
            p.created_at,
            p.updated_at,
            p.published_at,
            p.deactivated_at,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', pa.id,
                            'name', pa.name,
                            'slug', pa.slug
                        )
                        ORDER BY pa.name
                    )
                    FROM project_area_links pal
                    JOIN project_areas pa ON pa.id = pal.area_id
                    WHERE pal.project_id = p.id
                ),
                '[]'::jsonb
            ) AS areas,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', c.id,
                            'unit_id', c.unit_id,
                            'name', c.name,
                            'level', c.level,
                            'code', c.code,
                            'is_active', c.is_active
                        )
                        ORDER BY c.name
                    )
                    FROM project_course_links pcl
                    JOIN courses c ON c.id = pcl.course_id
                    WHERE pcl.project_id = p.id
                ),
                '[]'::jsonb
            ) AS cursos,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', pi.id,
                            'image_type', pi.image_type,
                            'image_url', pi.image_url,
                            'alt_text', pi.alt_text,
                            'sort_order', pi.sort_order
                        )
                        ORDER BY
                            CASE WHEN pi.image_type = 'cover' THEN 0 ELSE 1 END,
                            pi.sort_order,
                            pi.id
                    )
                    FROM project_images pi
                    WHERE pi.project_id = p.id
                ),
                '[]'::jsonb
            ) AS imagens
        FROM projects p
        LEFT JOIN professor_registry pr ON pr.id = p.owner_professor_id
        LEFT JOIN organizational_units ou ON ou.id = p.executing_unit_id
        LEFT JOIN project_types pt ON pt.id = p.project_type_id
        WHERE p.id = $1
          AND p.is_active = TRUE
          AND p.status = 'published'
          AND COALESCE(pt.is_enabled, TRUE) = TRUE
        LIMIT 1;
    """

    row = await conn.fetchrow(query, project_id)
    return {**row} if row else None


async def exists_public_project(conn: asyncpg.Connection, project_id: int) -> bool:
    query = """
        SELECT 1
        FROM projects p
        LEFT JOIN project_types pt ON pt.id = p.project_type_id
        WHERE p.id = $1
          AND p.is_active = TRUE
          AND p.status = 'published'
          AND COALESCE(pt.is_enabled, TRUE) = TRUE
        LIMIT 1;
    """

    row = await conn.fetchrow(query, project_id)
    return bool(row)


async def get_public_project_assignments(conn: asyncpg.Connection, project_id: int) -> list[dict]:
    query = """
        SELECT
            pa.id AS atribuicao_id,
            pa.project_id AS projeto_id,
            pa.description AS descricao,
            COALESCE(
                ARRAY_AGG(DISTINCT pac.course_id ORDER BY pac.course_id)
                    FILTER (WHERE pac.course_id IS NOT NULL),
                ARRAY[]::BIGINT[]
            ) AS curso_ids
        FROM project_assignments pa
        JOIN projects p ON p.id = pa.project_id
        LEFT JOIN project_types pt ON pt.id = p.project_type_id
        LEFT JOIN project_assignment_courses pac ON pac.project_assignment_id = pa.id
        WHERE pa.project_id = $1
          AND pa.is_active = TRUE
          AND p.is_active = TRUE
          AND p.status = 'published'
          AND COALESCE(pt.is_enabled, TRUE) = TRUE
        GROUP BY pa.id, pa.project_id, pa.description, pa.sort_order, pa.created_at
        ORDER BY pa.sort_order ASC, pa.created_at DESC;
    """

    rows = await conn.fetch(query, project_id)
    return [{**row} for row in rows]


async def get_user_managed_projects(
    conn: asyncpg.Connection,
    user_id: int,
    user_role: str,
    page: int,
    page_size: int,
    q: Optional[str],
) -> tuple[list[dict], int]:
    normalized_q = (q or "").strip()
    q_filter = f"%{normalized_q}%" if normalized_q else None

    count_query = """
        SELECT COUNT(*)::BIGINT AS total
        FROM projects p
        LEFT JOIN professor_registry pr ON pr.id = p.owner_professor_id
        LEFT JOIN organizational_units ou ON ou.id = p.executing_unit_id
        LEFT JOIN project_types pt ON pt.id = p.project_type_id
        WHERE p.is_active = TRUE
          AND (
              $1::TEXT = 'admin'
              OR pr.user_id = $2
          )
          AND (
              $3::TEXT IS NULL
              OR p.title ILIKE $3
              OR COALESCE(p.short_description, '') ILIKE $3
              OR COALESCE(p.full_description, '') ILIKE $3
          );
    """

    count_row = await conn.fetchrow(count_query, user_role, user_id, q_filter)
    total = int(count_row["total"]) if count_row else 0

    offset = (page - 1) * page_size

    query = """
        SELECT
            p.id,
            p.process_code,
            p.title,
            p.short_description,
            p.full_description,
            p.contact_email,
            p.owner_professor_id,
            pr.full_name AS owner_professor_name,
            p.executing_unit_id,
            ou.name AS executing_unit_name,
            ou.short_name AS executing_unit_short_name,
            ou.type AS executing_unit_type,
            p.source_import_batch_id,
            p.project_type_id,
            pt.name AS project_type_name,
            pt.slug AS project_type_slug,
            COALESCE(pt.is_enabled, TRUE) AS project_type_is_enabled,
            p.status,
            p.is_active,
            p.starts_at,
            p.ends_at,
            p.created_at,
            p.updated_at,
            p.published_at,
            p.deactivated_at,
            COALESCE(
                ARRAY(
                    SELECT pal.area_id
                    FROM project_area_links pal
                    WHERE pal.project_id = p.id
                    ORDER BY pal.area_id
                ),
                ARRAY[]::BIGINT[]
            ) AS area_ids,
            COALESCE(
                ARRAY(
                    SELECT pcl.course_id
                    FROM project_course_links pcl
                    WHERE pcl.project_id = p.id
                    ORDER BY pcl.course_id
                ),
                ARRAY[]::BIGINT[]
            ) AS course_ids
        FROM projects p
        LEFT JOIN professor_registry pr ON pr.id = p.owner_professor_id
        LEFT JOIN organizational_units ou ON ou.id = p.executing_unit_id
        LEFT JOIN project_types pt ON pt.id = p.project_type_id
        WHERE p.is_active = TRUE
          AND (
              $1::TEXT = 'admin'
              OR pr.user_id = $2
          )
          AND (
              $3::TEXT IS NULL
              OR p.title ILIKE $3
              OR COALESCE(p.short_description, '') ILIKE $3
              OR COALESCE(p.full_description, '') ILIKE $3
          )
        ORDER BY p.updated_at DESC, p.id DESC
        LIMIT $4
        OFFSET $5;
    """

    rows = await conn.fetch(query, user_role, user_id, q_filter, page_size, offset)
    return [{**row} for row in rows], total


async def update_managed_project_fields(
    conn: asyncpg.Connection,
    project_id: int,
    user_id: int,
    user_role: str,
    allowed_fields: dict[str, str],
) -> dict | None:
    updates: list[str] = []
    params: list[object] = [project_id, user_role, user_id]

    for field_name, field_value in allowed_fields.items():
        if field_name not in MANAGED_PROJECT_UPDATE_COLUMNS:
            continue
        params.append(field_value)
        updates.append(f"{field_name} = ${len(params)}")

    if not updates:
        return None

    updates.append("updated_at = NOW()")

    query = f"""
        WITH updated_project AS (
            UPDATE projects p
            SET {', '.join(updates)}
            WHERE p.id = $1
              AND p.is_active = TRUE
              AND (
                  $2::TEXT = 'admin'
                  OR EXISTS (
                      SELECT 1
                      FROM professor_registry pr_access
                      WHERE pr_access.id = p.owner_professor_id
                        AND pr_access.user_id = $3
                  )
              )
            RETURNING p.*
        )
        SELECT
            up.id,
            up.process_code,
            up.title,
            up.short_description,
            up.full_description,
            up.contact_email,
            up.owner_professor_id,
            pr.full_name AS owner_professor_name,
            up.executing_unit_id,
            ou.name AS executing_unit_name,
            ou.short_name AS executing_unit_short_name,
            ou.type AS executing_unit_type,
            up.source_import_batch_id,
            up.project_type_id,
            pt.name AS project_type_name,
            pt.slug AS project_type_slug,
            COALESCE(pt.is_enabled, TRUE) AS project_type_is_enabled,
            up.status,
            up.is_active,
            up.starts_at,
            up.ends_at,
            up.created_at,
            up.updated_at,
            up.published_at,
            up.deactivated_at,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', pa.id,
                            'name', pa.name,
                            'slug', pa.slug
                        )
                        ORDER BY pa.name
                    )
                    FROM project_area_links pal
                    JOIN project_areas pa ON pa.id = pal.area_id
                    WHERE pal.project_id = up.id
                ),
                '[]'::jsonb
            ) AS areas,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', c.id,
                            'unit_id', c.unit_id,
                            'name', c.name,
                            'level', c.level,
                            'code', c.code,
                            'is_active', c.is_active
                        )
                        ORDER BY c.name
                    )
                    FROM project_course_links pcl
                    JOIN courses c ON c.id = pcl.course_id
                    WHERE pcl.project_id = up.id
                ),
                '[]'::jsonb
            ) AS cursos,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', pi.id,
                            'image_type', pi.image_type,
                            'image_url', pi.image_url,
                            'alt_text', pi.alt_text,
                            'sort_order', pi.sort_order
                        )
                        ORDER BY
                            CASE WHEN pi.image_type = 'cover' THEN 0 ELSE 1 END,
                            pi.sort_order,
                            pi.id
                    )
                    FROM project_images pi
                    WHERE pi.project_id = up.id
                ),
                '[]'::jsonb
            ) AS imagens
        FROM updated_project up
        LEFT JOIN professor_registry pr ON pr.id = up.owner_professor_id
        LEFT JOIN organizational_units ou ON ou.id = up.executing_unit_id
        LEFT JOIN project_types pt ON pt.id = up.project_type_id
        LIMIT 1;
    """

    row = await conn.fetchrow(query, *params)
    return {**row} if row else None


async def upsert_project_cover_image(
    conn: asyncpg.Connection,
    project_id: int,
    user_id: int,
    user_role: str,
    image_url: str,
    alt_text: Optional[str],
) -> dict | None:
    query = """
        WITH managed_project AS (
            SELECT p.id
            FROM projects p
            WHERE p.id = $1
              AND p.is_active = TRUE
              AND (
                  $2::TEXT = 'admin'
                  OR EXISTS (
                      SELECT 1
                      FROM professor_registry pr
                      WHERE pr.id = p.owner_professor_id
                        AND pr.user_id = $3
                  )
              )
            LIMIT 1
        )
        INSERT INTO project_images (
            project_id,
            image_type,
            image_url,
            alt_text,
            sort_order,
            created_at
        )
        SELECT mp.id, 'cover', $4, $5, 0, NOW()
        FROM managed_project mp
        ON CONFLICT (project_id)
        WHERE image_type = 'cover'
        DO UPDATE SET
            image_url = EXCLUDED.image_url,
            alt_text = EXCLUDED.alt_text,
            sort_order = 0
        RETURNING project_id AS projeto_id, image_url, alt_text;
    """

    row = await conn.fetchrow(query, project_id, user_role, user_id, image_url, alt_text)
    return {**row} if row else None


async def create_project_assignment(
    conn: asyncpg.Connection,
    project_id: int,
    user_id: int,
    user_role: str,
    descricao: str,
    course_ids: list[int],
) -> dict:
    query = """
        WITH managed_project AS (
            SELECT p.id
            FROM projects p
            WHERE p.id = $1
              AND p.is_active = TRUE
              AND (
                  $2::TEXT = 'admin'
                  OR EXISTS (
                      SELECT 1
                      FROM professor_registry pr
                      WHERE pr.id = p.owner_professor_id
                        AND pr.user_id = $3
                  )
              )
            LIMIT 1
        ),
        validated_courses AS (
            SELECT DISTINCT pcl.course_id
            FROM project_course_links pcl
            JOIN courses c ON c.id = pcl.course_id
            WHERE pcl.project_id = $1
              AND c.is_active = TRUE
              AND pcl.course_id = ANY($4::BIGINT[])
        ),
        inserted_assignment AS (
            INSERT INTO project_assignments (
                project_id,
                description,
                sort_order,
                is_active,
                created_at,
                updated_at
            )
            SELECT
                mp.id,
                $5,
                COALESCE(
                    (
                        SELECT MAX(pa.sort_order) + 1
                        FROM project_assignments pa
                        WHERE pa.project_id = mp.id
                    ),
                    0
                ),
                TRUE,
                NOW(),
                NOW()
            FROM managed_project mp
            WHERE (SELECT COUNT(*) FROM validated_courses) = $6
            RETURNING id, project_id, description
        ),
        inserted_course_links AS (
            INSERT INTO project_assignment_courses (project_assignment_id, course_id)
            SELECT ia.id, vc.course_id
            FROM inserted_assignment ia
            JOIN validated_courses vc ON TRUE
            ON CONFLICT (project_assignment_id, course_id) DO NOTHING
            RETURNING course_id
        )
        SELECT
            EXISTS(SELECT 1 FROM managed_project) AS has_project_access,
            (SELECT COUNT(*)::INT FROM validated_courses) AS valid_course_count,
            $6::INT AS requested_course_count,
            ia.id AS atribuicao_id,
            ia.project_id AS projeto_id,
            ia.description AS descricao,
            COALESCE(
                (
                    SELECT ARRAY_AGG(icl.course_id ORDER BY icl.course_id)
                    FROM inserted_course_links icl
                ),
                ARRAY[]::BIGINT[]
            ) AS curso_ids
        FROM (SELECT 1) AS base
        LEFT JOIN inserted_assignment ia ON TRUE;
    """

    row = await conn.fetchrow(
        query,
        project_id,
        user_role,
        user_id,
        course_ids,
        descricao,
        len(course_ids),
    )

    if not row:
        return {
            "has_project_access": False,
            "valid_course_count": 0,
            "requested_course_count": len(course_ids),
            "assignment": None,
        }

    assignment = None
    if row["atribuicao_id"] is not None:
        assignment = {
            "atribuicao_id": int(row["atribuicao_id"]),
            "projeto_id": int(row["projeto_id"]),
            "descricao": row["descricao"],
            "curso_ids": [int(course_id) for course_id in row["curso_ids"]],
        }

    return {
        "has_project_access": bool(row["has_project_access"]),
        "valid_course_count": int(row["valid_course_count"]),
        "requested_course_count": int(row["requested_course_count"]),
        "assignment": assignment,
    }


async def get_manageable_assignment_by_id(
    conn: asyncpg.Connection,
    assignment_id: int,
    user_id: int,
    user_role: str,
) -> dict | None:
    query = """
        SELECT
            pa.id AS atribuicao_id,
            pa.project_id AS projeto_id
        FROM project_assignments pa
        JOIN projects p ON p.id = pa.project_id
        LEFT JOIN professor_registry pr ON pr.id = p.owner_professor_id
        WHERE pa.id = $1
          AND pa.is_active = TRUE
          AND p.is_active = TRUE
          AND (
              $2::TEXT = 'admin'
              OR pr.user_id = $3
          )
        LIMIT 1;
    """

    row = await conn.fetchrow(query, assignment_id, user_role, user_id)
    return {**row} if row else None


async def deactivate_project_assignment(
    conn: asyncpg.Connection,
    assignment_id: int,
    user_id: int,
    user_role: str,
) -> bool:
    query = """
        UPDATE project_assignments pa
        SET is_active = FALSE,
            updated_at = NOW()
        FROM projects p
        LEFT JOIN professor_registry pr ON pr.id = p.owner_professor_id
        WHERE pa.id = $1
          AND pa.project_id = p.id
          AND pa.is_active = TRUE
          AND p.is_active = TRUE
          AND (
              $2::TEXT = 'admin'
              OR pr.user_id = $3
          )
        RETURNING pa.id;
    """

    row = await conn.fetchrow(query, assignment_id, user_role, user_id)
    return bool(row)
