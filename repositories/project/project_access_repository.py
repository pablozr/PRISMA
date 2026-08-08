import asyncpg


async def can_edit_project(
    conn: asyncpg.Connection,
    project_id: int,
    user_id: int,
    user_role: str,
) -> bool:
    if user_role == "admin":
        return True

    allowed = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1
            FROM project_edit_permissions permission
            JOIN people person ON person.id = permission.person_id
            WHERE permission.project_id = $1
              AND person.user_id = $2
              AND permission.is_active = TRUE
        );
        """,
        project_id,
        user_id,
    )
    return bool(allowed)
