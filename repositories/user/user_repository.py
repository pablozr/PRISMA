import asyncpg


async def get_active_user_by_email(conn: asyncpg.Connection, email: str) -> dict | None:
    query = """
            SELECT id,
                   institutional_email,
                   full_name,
                   role,
                   google_sub,
                   is_active
            FROM users
            WHERE institutional_email = $1
              AND is_active = TRUE LIMIT 1; \
            """
    result = await conn.fetchrow(query, email)

    return {**result} if result else None