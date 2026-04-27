import asyncpg

from schemas.professor.professor import CreateProfessorSchema


async def create_user_professor_registry(conn: asyncpg.Connection, data: CreateProfessorSchema) -> dict | None:
    create_professor_query = """
                             WITH created_user AS (
                             INSERT
                             INTO users (institutional_email,
                                         full_name,
                                         google_sub,
                                         role,
                                         is_active,
                                         last_login_at,
                                         created_at,
                                         updated_at)
                             VALUES (
                                 $1, $2, $3, 'professor', TRUE, NOW(), NOW(), NOW()
                                 )
                                 RETURNING
                                 id, institutional_email, full_name, role, google_sub, is_active, created_at, updated_at
                                 ), updated_professor AS (
                             UPDATE professor_registry pr
                             SET
                                 user_id = cu.id, updated_at = NOW()
                             FROM created_user cu
                             WHERE pr.institutional_email = cu.institutional_email
                               AND pr.is_active = TRUE
                               AND pr.user_id IS NULL
                                 RETURNING
                                 pr.id AS professor_registry_id
                                 , pr.user_id
                                 )
                             SELECT cu.id,
                                    cu.institutional_email,
                                    cu.full_name,
                                    cu.role,
                                    cu.google_sub,
                                    cu.is_active,
                                    cu.created_at,
                                    cu.updated_at,
                                    up.professor_registry_id
                             FROM created_user cu
                                      LEFT JOIN updated_professor up ON up.user_id = cu.id; \
                             """

    row = await conn.fetchrow(create_professor_query, data.institutional_email, data.full_name, data.google_sub)
    return {**row} if row else None


async def get_active_professor_by_email(conn: asyncpg.Connection, email: str) -> dict | None:
    query = """
            SELECT id,
                   institutional_email,
                   full_name,
                   siape,
                   department_unit_id,
                   user_id,
                   is_active
            FROM professor_registry
            WHERE institutional_email = $1
              AND is_active = TRUE LIMIT 1; 
            """

    row = await conn.fetchrow(query, email)
    return {**row} if row else None
