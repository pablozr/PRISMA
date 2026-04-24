from typing import List

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
            SELECT id, \
                   name, \
                   short_name
            FROM organizational_units
            WHERE type = 'centro'
              AND is_active = TRUE
            ORDER BY name ASC
                LIMIT $1
            OFFSET $2; \
            """

    rows = await conn.fetch(query, limit, offset)
    return [{**row} for row in rows]
