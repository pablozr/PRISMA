from schemas.admin import (
    AdminProjectUpdateRequest,
    AdminProjectsListQuery,
    AdminUserUpdateRequest,
    AdminUsersListQuery,
)


async def get_dashboard_metrics(conn) -> dict:
    query = """
        SELECT
            (SELECT COUNT(*)::BIGINT FROM projects) AS total_projects,
            (SELECT COUNT(*)::BIGINT FROM projects WHERE is_active = FALSE) AS inactive_projects,
            (SELECT COUNT(*)::BIGINT FROM users) AS total_users,
            (SELECT COUNT(*)::BIGINT FROM users WHERE is_active = TRUE) AS active_users;
    """

    row = await conn.fetchrow(query)
    return {
        "status": True,
        "message": "Metricas carregadas com sucesso.",
        "data": {
            "metrics": {
                "total_projects": int(row["total_projects"]) if row else 0,
                "inactive_projects": int(row["inactive_projects"]) if row else 0,
                "total_users": int(row["total_users"]) if row else 0,
                "active_users": int(row["active_users"]) if row else 0,
            }
        },
    }


async def list_users(conn, query: AdminUsersListQuery) -> dict:
    normalized_q = (query.q or "").strip()
    q_filter = f"%{normalized_q}%" if normalized_q else None

    count_query = """
        SELECT COUNT(*)::BIGINT AS total
        FROM users u
        WHERE $1::TEXT IS NULL
           OR u.full_name ILIKE $1
           OR u.institutional_email::TEXT ILIKE $1;
    """
    count_row = await conn.fetchrow(count_query, q_filter)
    total = int(count_row["total"]) if count_row else 0

    offset = (query.page - 1) * query.page_size
    list_query = """
        SELECT
            u.id,
            u.institutional_email,
            u.full_name,
            u.role,
            u.is_active,
            u.created_at,
            u.last_login_at
        FROM users u
        WHERE $1::TEXT IS NULL
           OR u.full_name ILIKE $1
           OR u.institutional_email::TEXT ILIKE $1
        ORDER BY u.created_at DESC, u.id DESC
        LIMIT $2
        OFFSET $3;
    """
    rows = await conn.fetch(list_query, q_filter, query.page_size, offset)
    users = [{**row} for row in rows]
    total_pages = (total + query.page_size - 1) // query.page_size if total else 0

    return {
        "status": True,
        "message": "Usuarios carregados com sucesso.",
        "data": {
            "users": users,
            "pagination": {
                "page": query.page,
                "page_size": query.page_size,
                "total": total,
                "total_pages": total_pages,
            },
        },
    }


async def update_user(conn, user_id: int, payload: AdminUserUpdateRequest) -> dict:
    updates: list[str] = []
    params: list[object] = [user_id]

    if payload.role is not None:
        params.append(payload.role)
        updates.append(f"role = ${len(params)}")

    if payload.is_active is not None:
        params.append(payload.is_active)
        updates.append(f"is_active = ${len(params)}")

    if not updates:
        return {"status": False, "message": "Nenhum campo valido informado para atualizacao.", "data": {}}

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

    if not row:
        return {"status": False, "message": "Usuario nao encontrado.", "data": {}}

    return {
        "status": True,
        "message": "Usuario atualizado com sucesso.",
        "data": {"user": {**row}},
    }


async def list_projects(conn, query: AdminProjectsListQuery) -> dict:
    normalized_q = (query.q or "").strip()
    q_filter = f"%{normalized_q}%" if normalized_q else None

    count_query = """
        SELECT COUNT(*)::BIGINT AS total
        FROM projects p
        LEFT JOIN users ru ON ru.id = p.responsible_user_id
        WHERE $1::TEXT IS NULL
           OR p.title ILIKE $1
           OR COALESCE(p.short_description, '') ILIKE $1
           OR COALESCE(ru.full_name, '') ILIKE $1
           OR COALESCE(ru.institutional_email::TEXT, '') ILIKE $1;
    """
    count_row = await conn.fetchrow(count_query, q_filter)
    total = int(count_row["total"]) if count_row else 0

    offset = (query.page - 1) * query.page_size
    list_query = """
        SELECT
            p.id,
            p.process_code,
            p.title,
            p.short_description,
            p.status,
            p.is_active,
            p.updated_at,
            p.published_at,
            p.responsible_user_id AS responsible_id,
            ru.full_name AS responsible_name,
            ru.institutional_email::TEXT AS responsible_email,
            CASE
                WHEN ru.role = 'tecnico' THEN 'tecnico'
                ELSE 'docente'
            END AS responsible_type
        FROM projects p
        LEFT JOIN users ru ON ru.id = p.responsible_user_id
        WHERE $1::TEXT IS NULL
           OR p.title ILIKE $1
           OR COALESCE(p.short_description, '') ILIKE $1
           OR COALESCE(ru.full_name, '') ILIKE $1
           OR COALESCE(ru.institutional_email::TEXT, '') ILIKE $1
        ORDER BY p.updated_at DESC, p.id DESC
        LIMIT $2
        OFFSET $3;
    """
    rows = await conn.fetch(list_query, q_filter, query.page_size, offset)
    projects = [{**row} for row in rows]
    total_pages = (total + query.page_size - 1) // query.page_size if total else 0

    return {
        "status": True,
        "message": "Projetos carregados com sucesso.",
        "data": {
            "projects": projects,
            "pagination": {
                "page": query.page,
                "page_size": query.page_size,
                "total": total,
                "total_pages": total_pages,
            },
        },
    }


async def update_project(conn, project_id: int, payload: AdminProjectUpdateRequest) -> dict:
    updates: list[str] = []
    params: list[object] = [project_id]

    if payload.status is not None:
        params.append(payload.status)
        updates.append(f"status = ${len(params)}")

    if payload.is_active is not None:
        params.append(payload.is_active)
        updates.append(f"is_active = ${len(params)}")
        if payload.is_active:
            updates.append("deactivated_at = NULL")
        else:
            updates.append("deactivated_at = NOW()")

    if not updates:
        return {"status": False, "message": "Nenhum campo valido informado para atualizacao.", "data": {}}

    updates.append("updated_at = NOW()")

    query = f"""
        UPDATE projects p
        SET {', '.join(updates)}
        WHERE p.id = $1
        RETURNING
            p.id,
            p.process_code,
            p.title,
            p.short_description,
            p.status,
            p.is_active,
            p.updated_at,
            p.published_at,
            p.responsible_user_id AS responsible_id;
    """
    row = await conn.fetchrow(query, *params)

    if not row:
        return {"status": False, "message": "Projeto nao encontrado.", "data": {}}

    return {
        "status": True,
        "message": "Projeto atualizado com sucesso.",
        "data": {"project": {**row}},
    }
