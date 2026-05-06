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
              AND is_active = TRUE
            LIMIT 1;
            """

    result = await conn.fetchrow(query, email)
    return {**result} if result else None


async def get_active_user_with_password_by_email(conn: asyncpg.Connection, email: str) -> dict | None:
    query = """
            SELECT id,
                   institutional_email,
                   password_hash,
                   role
            FROM users
            WHERE institutional_email = $1
              AND is_active = TRUE
            LIMIT 1;
            """

    row = await conn.fetchrow(query, email)
    return {**row} if row else None


async def get_active_user_for_password_reset(conn: asyncpg.Connection, email: str) -> dict | None:
    query = """
            SELECT id,
                   full_name,
                   institutional_email,
                   role
            FROM users
            WHERE institutional_email = $1
              AND is_active = TRUE
            LIMIT 1;
            """

    row = await conn.fetchrow(query, email)
    return {**row} if row else None


async def get_active_user_by_id(conn: asyncpg.Connection, user_id: int) -> dict | None:
    query = """
            SELECT id,
                   institutional_email,
                   full_name,
                   role,
                   is_active
            FROM users
            WHERE id = $1
              AND is_active = TRUE
            LIMIT 1;
            """

    row = await conn.fetchrow(query, user_id)
    return {**row} if row else None


async def update_user_password(conn: asyncpg.Connection, user_id: int, password_hash: str) -> dict | None:
    query = """
            UPDATE users
            SET password_hash = $1,
                updated_at = NOW()
            WHERE id = $2
              AND is_active = TRUE
            RETURNING
                id,
                institutional_email,
                full_name,
                role,
                is_active,
                created_at,
                updated_at;
            """

    row = await conn.fetchrow(query, password_hash, user_id)
    return {**row} if row else None


async def count_users(conn: asyncpg.Connection, q: str | None) -> int:
    query = """
            SELECT COUNT(*)::BIGINT AS total
            FROM users u
            WHERE NULLIF(TRIM($1::TEXT), '') IS NULL
               OR u.full_name ILIKE ('%' || TRIM($1::TEXT) || '%')
               OR u.institutional_email::TEXT ILIKE ('%' || TRIM($1::TEXT) || '%');
            """

    row = await conn.fetchrow(query, q)
    return int(row["total"]) if row else 0


async def list_users_paginated(
    conn: asyncpg.Connection,
    q: str | None,
    page_size: int,
    offset: int,
) -> list[dict]:
    query = """
            SELECT
                u.id,
                u.institutional_email,
                u.full_name,
                u.role,
                u.is_active,
                u.created_at,
                u.last_login_at
            FROM users u
            WHERE NULLIF(TRIM($1::TEXT), '') IS NULL
               OR u.full_name ILIKE ('%' || TRIM($1::TEXT) || '%')
               OR u.institutional_email::TEXT ILIKE ('%' || TRIM($1::TEXT) || '%')
            ORDER BY u.created_at DESC, u.id DESC
            LIMIT $2
            OFFSET $3;
            """

    rows = await conn.fetch(query, q, page_size, offset)
    return [{**row} for row in rows]


async def update_user_fields(
    conn: asyncpg.Connection,
    user_id: int,
    role: str | None,
    is_active: bool | None,
) -> dict | None:
    updates: list[str] = []
    params: list[object] = [user_id]

    if role is not None:
        params.append(role)
        updates.append(f"role = ${len(params)}")

    if is_active is not None:
        params.append(is_active)
        updates.append(f"is_active = ${len(params)}")

    if not updates:
        return None

    updates.append("updated_at = NOW()")
    query = f"""
            UPDATE users u
            SET {', '.join(updates)}
            WHERE u.id = $1
            RETURNING
                u.id,
                u.institutional_email,
                u.full_name,
                u.role,
                u.is_active,
                u.created_at,
                u.last_login_at;
            """

    row = await conn.fetchrow(query, *params)
    return {**row} if row else None
