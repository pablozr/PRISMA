from typing import List, Optional

import asyncpg


async def get_all_areas_tematicas(conn: asyncpg.Connection, limit: int, offset: int) -> List[dict]:
    query = """
            SELECT id,
                   name,
                   slug
            FROM project_areas
            ORDER BY name ASC
                LIMIT $1
            OFFSET $2;
            """

    rows = await conn.fetch(query, limit, offset)
    return [{**row} for row in rows]


async def get_all_centros(conn: asyncpg.Connection, limit: int, offset: int) -> List[dict]:
    query = """
            SELECT id,
                   name,
                   NULL::TEXT AS short_name
            FROM organizational_units
            WHERE unit_type = 'centro'
              AND is_active = TRUE
            ORDER BY name ASC
            LIMIT $1
            OFFSET $2;
            """

    rows = await conn.fetch(query, limit, offset)
    return [{**row} for row in rows]


async def get_all_unidades(
    conn: asyncpg.Connection,
    centro_ids: Optional[list[int]],
    limit: int,
    offset: int,
) -> List[dict]:
    query = """
            SELECT id,
                   name,
                   NULL::TEXT AS short_name,
                   unit_type AS type,
                   parent_unit_id
            FROM organizational_units
            WHERE unit_type = 'unidade'
              AND is_active = TRUE
              AND ($1::BIGINT[] IS NULL OR parent_unit_id = ANY($1::BIGINT[]))
            ORDER BY name ASC
            LIMIT $2
            OFFSET $3;
            """

    rows = await conn.fetch(query, centro_ids, limit, offset)
    return [{**row} for row in rows]


async def get_all_cursos(
    conn: asyncpg.Connection,
    unidade_ids: Optional[list[int]],
    limit: int,
    offset: int,
) -> List[dict]:
    query = """
            SELECT c.id,
                   c.name,
                   NULL::TEXT AS level,
                   c.code,
                   c.offering_unit_id,
                   ou.name AS offering_unit_name,
                   NULL::TEXT AS offering_unit_short_name,
                   ou.unit_type AS offering_unit_type
            FROM courses c
            JOIN organizational_units ou ON ou.id = c.offering_unit_id
            WHERE c.is_active = TRUE
              AND ou.is_active = TRUE
              AND ou.unit_type = 'unidade'
              AND ($1::BIGINT[] IS NULL OR c.offering_unit_id = ANY($1::BIGINT[]))
            ORDER BY c.name ASC
            LIMIT $2
            OFFSET $3;
            """

    rows = await conn.fetch(query, unidade_ids, limit, offset)
    return [{**row} for row in rows]
