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
                   short_name
            FROM organizational_units
            WHERE type = 'centro'
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
                   short_name,
                   type,
                   parent_unit_id
            FROM organizational_units
            WHERE type IN ('instituto', 'escola')
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
                   c.level,
                   c.code,
                   c.offering_unit_id,
                   ou.name AS offering_unit_name,
                   ou.short_name AS offering_unit_short_name,
                   ou.type AS offering_unit_type
            FROM courses c
            JOIN organizational_units ou ON ou.id = c.offering_unit_id
            WHERE c.is_active = TRUE
              AND ou.is_active = TRUE
              AND ou.type IN ('instituto', 'escola')
              AND ($1::BIGINT[] IS NULL OR c.offering_unit_id = ANY($1::BIGINT[]))
            ORDER BY c.name ASC
            LIMIT $2
            OFFSET $3;
            """

    rows = await conn.fetch(query, unidade_ids, limit, offset)
    return [{**row} for row in rows]
