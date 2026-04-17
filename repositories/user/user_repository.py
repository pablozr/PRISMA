import asyncpg

from schemas.user.user import CreateStudentUserSchema


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


async def create_student_user(conn: asyncpg.Connection, data: CreateStudentUserSchema) -> dict | None:
    query = """
            INSERT INTO users (
                institutional_email,
                full_name,
                google_sub,
                role,
                is_active,
                last_login_at,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, 'student', TRUE, NOW(), NOW(), NOW())
            RETURNING
                id,
                institutional_email,
                full_name,
                role,
                google_sub,
                is_active,
                created_at,
                updated_at;
            """

    row = await conn.fetchrow(query, data.institutional_email, data.full_name, data.google_sub)
    return {**row} if row else None