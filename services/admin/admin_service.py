from functions.utils.utils import build_pagination, get_pagination_offset, service_response

from repositories.admin.admin_repository import (
    count_admin_projects,
    count_import_batches,
    count_import_errors_by_batch,
    get_dashboard_metrics_row,
    list_admin_projects_paginated,
    list_import_batches_paginated,
    list_import_errors_by_batch_paginated,
    update_admin_project_fields,
)
from repositories.user.user_repository import count_users, list_users_paginated, update_user_fields
from schemas.admin import (
    AdminImportErrorsListQuery,
    AdminImportsListQuery,
    AdminProjectUpdateRequest,
    AdminProjectsListQuery,
    AdminUserUpdateRequest,
    AdminUsersListQuery,
)


async def get_dashboard_metrics(conn) -> dict:
    row = await get_dashboard_metrics_row(conn)
    return service_response(
        status=True,
        message="Metricas carregadas com sucesso.",
        data={
            "metrics": {
                "total_projects": int(row["total_projects"]) if row else 0,
                "inactive_projects": int(row["inactive_projects"]) if row else 0,
                "total_users": int(row["total_users"]) if row else 0,
                "active_users": int(row["active_users"]) if row else 0,
            }
        },
    )


async def list_users(conn, query: AdminUsersListQuery) -> dict:
    total = await count_users(conn, query.q)

    offset = get_pagination_offset(query.page, query.page_size)
    users = await list_users_paginated(conn, query.q, query.page_size, offset)

    return service_response(
        status=True,
        message="Usuarios carregados com sucesso.",
        data={
            "users": users,
            "pagination": build_pagination(query.page, query.page_size, total),
        },
    )


async def update_user(conn, user_id: int, payload: AdminUserUpdateRequest) -> dict:
    if payload.role is None and payload.is_active is None:
        return service_response(status=False, message="Nenhum campo valido informado para atualizacao.")

    row = await update_user_fields(conn, user_id, payload.role, payload.is_active)

    if not row:
        return service_response(status=False, message="Usuario nao encontrado.")

    return service_response(status=True, message="Usuario atualizado com sucesso.", data={"user": {**row}})


async def list_projects(conn, query: AdminProjectsListQuery) -> dict:
    total = await count_admin_projects(conn, query.q)

    offset = get_pagination_offset(query.page, query.page_size)
    projects = await list_admin_projects_paginated(conn, query.q, query.page_size, offset)

    return service_response(
        status=True,
        message="Projetos carregados com sucesso.",
        data={
            "projects": projects,
            "pagination": build_pagination(query.page, query.page_size, total),
        },
    )


async def update_project(conn, project_id: int, payload: AdminProjectUpdateRequest) -> dict:
    if payload.status is None and payload.is_active is None:
        return service_response(status=False, message="Nenhum campo valido informado para atualizacao.")

    row = await update_admin_project_fields(conn, project_id, payload.status, payload.is_active)

    if not row:
        return service_response(status=False, message="Projeto nao encontrado.")

    return service_response(status=True, message="Projeto atualizado com sucesso.", data={"project": {**row}})


async def list_import_batches(conn, query: AdminImportsListQuery) -> dict:
    total = await count_import_batches(conn)

    offset = get_pagination_offset(query.page, query.page_size)
    rows = await list_import_batches_paginated(conn, query.page_size, offset)

    return service_response(
        status=True,
        message="Historico de importacoes carregado com sucesso.",
        data={
            "batches": rows,
            "pagination": build_pagination(query.page, query.page_size, total),
        },
    )


async def list_import_errors(conn, batch_id: int, query: AdminImportErrorsListQuery) -> dict:
    total = await count_import_errors_by_batch(conn, batch_id)

    offset = get_pagination_offset(query.page, query.page_size)
    rows = await list_import_errors_by_batch_paginated(conn, batch_id, query.page_size, offset)

    return service_response(
        status=True,
        message="Erros de importacao carregados com sucesso.",
        data={
            "errors": rows,
            "pagination": build_pagination(query.page, query.page_size, total),
        },
    )
