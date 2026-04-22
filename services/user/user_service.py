from schemas.user import UserGetResponse


async def get_one_user(conn, user_id: int) -> dict:
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

    if not row:
        return {"status": False, "message": "User not found", "data": dict()}

    return {
        "status": True,
        "message": "User retrieved successfully",
        "data": {
            "user": {
                "id": row["id"],
                "institutional_email": row["institutional_email"],
                "full_name": row["full_name"],
                "role": row["role"],
                "is_active": row["is_active"],
            }
        }
    }
