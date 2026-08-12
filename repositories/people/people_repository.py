import asyncpg


async def get_person_by_email(conn: asyncpg.Connection, email: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT id, institutional_email, full_name, profile, user_id
        FROM people
        WHERE institutional_email = $1
        LIMIT 1;
        """,
        email,
    )
    return dict(row) if row else None


async def link_existing_user_to_person(conn: asyncpg.Connection, user_id: int, email: str) -> None:
    await conn.execute(
        """UPDATE people SET user_id=$1, updated_at=NOW()
           WHERE institutional_email=$2 AND user_id IS NULL""",
        user_id,
        email,
    )


async def create_user_from_person(conn: asyncpg.Connection, email: str, google_sub: str) -> dict | None:
    row = await conn.fetchrow(
        """
        WITH imported_person AS (
            SELECT id, institutional_email, full_name, profile
            FROM people
            WHERE institutional_email = $1 AND user_id IS NULL
            FOR UPDATE
        ), created_user AS (
            INSERT INTO users (institutional_email, full_name, role, role_source, google_sub)
            SELECT institutional_email, full_name, profile,
                   CASE WHEN profile IN ('professor', 'tecnico') THEN 'sie' ELSE 'google_default' END,
                   $2
            FROM imported_person
            RETURNING id, institutional_email, full_name, role, google_sub, is_active, created_at, updated_at
        ), linked_person AS (
            UPDATE people p SET user_id = cu.id, updated_at = NOW()
            FROM created_user cu
            WHERE p.institutional_email = cu.institutional_email
            RETURNING p.id AS person_id
        )
        SELECT cu.*, lp.person_id FROM created_user cu JOIN linked_person lp ON TRUE;
        """,
        email,
        google_sub,
    )
    return dict(row) if row else None
