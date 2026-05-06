import csv
import hashlib
from datetime import datetime
from io import StringIO

from fastapi import UploadFile
from functions.utils.utils import build_pagination, get_pagination_offset

from repositories.admin.admin_repository import (
    count_admin_projects,
    count_import_batches,
    count_import_errors_by_batch,
    create_import_batch_row,
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
    total = await count_users(conn, query.q)

    offset = get_pagination_offset(query.page, query.page_size)
    users = await list_users_paginated(conn, query.q, query.page_size, offset)

    return {
        "status": True,
        "message": "Usuarios carregados com sucesso.",
        "data": {
            "users": users,
            "pagination": build_pagination(query.page, query.page_size, total),
        },
    }


async def update_user(conn, user_id: int, payload: AdminUserUpdateRequest) -> dict:
    if payload.role is None and payload.is_active is None:
        return {"status": False, "message": "Nenhum campo valido informado para atualizacao.", "data": {}}

    row = await update_user_fields(conn, user_id, payload.role, payload.is_active)

    if not row:
        return {"status": False, "message": "Usuario nao encontrado.", "data": {}}

    return {
        "status": True,
        "message": "Usuario atualizado com sucesso.",
        "data": {"user": {**row}},
    }


async def list_projects(conn, query: AdminProjectsListQuery) -> dict:
    total = await count_admin_projects(conn, query.q)

    offset = get_pagination_offset(query.page, query.page_size)
    projects = await list_admin_projects_paginated(conn, query.q, query.page_size, offset)

    return {
        "status": True,
        "message": "Projetos carregados com sucesso.",
        "data": {
            "projects": projects,
            "pagination": build_pagination(query.page, query.page_size, total),
        },
    }


async def update_project(conn, project_id: int, payload: AdminProjectUpdateRequest) -> dict:
    if payload.status is None and payload.is_active is None:
        return {"status": False, "message": "Nenhum campo valido informado para atualizacao.", "data": {}}

    row = await update_admin_project_fields(conn, project_id, payload.status, payload.is_active)

    if not row:
        return {"status": False, "message": "Projeto nao encontrado.", "data": {}}

    return {
        "status": True,
        "message": "Projeto atualizado com sucesso.",
        "data": {"project": {**row}},
    }


def _infer_reference_term(now: datetime) -> int:
    return 1 if now.month <= 6 else 2


def _count_csv_rows(file_bytes: bytes) -> int:
    try:
        content = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = file_bytes.decode("latin-1")

    reader = csv.reader(StringIO(content))
    rows = [row for row in reader if any((cell or "").strip() for cell in row)]
    if not rows:
        return 0
    return max(len(rows) - 1, 0)


async def create_import_batch(conn, uploaded_by_user_id: int, file: UploadFile) -> dict:
    filename = file.filename or "import.csv"
    lower_name = filename.lower()
    if not (lower_name.endswith(".csv") or lower_name.endswith(".xlsx")):
        return {
            "status": False,
            "message": "Formato invalido. Envie um arquivo .csv ou .xlsx.",
            "data": {},
        }

    file_bytes = await file.read()
    if not file_bytes:
        return {"status": False, "message": "Arquivo vazio.", "data": {}}

    now = datetime.utcnow()
    source_hash = hashlib.sha256(file_bytes).hexdigest()
    total_rows = _count_csv_rows(file_bytes) if lower_name.endswith(".csv") else 0

    row = await create_import_batch_row(
        conn,
        now.year,
        _infer_reference_term(now),
        uploaded_by_user_id,
        filename,
        source_hash,
        total_rows,
    )

    return {
        "status": True,
        "message": "Arquivo importado com sucesso.",
        "data": {"batch": {**row}},
    }


async def list_import_batches(conn, query: AdminImportsListQuery) -> dict:
    total = await count_import_batches(conn)

    offset = get_pagination_offset(query.page, query.page_size)
    rows = await list_import_batches_paginated(conn, query.page_size, offset)

    return {
        "status": True,
        "message": "Historico de importacoes carregado com sucesso.",
        "data": {
            "batches": rows,
            "pagination": build_pagination(query.page, query.page_size, total),
        },
    }


async def list_import_errors(conn, batch_id: int, query: AdminImportErrorsListQuery) -> dict:
    total = await count_import_errors_by_batch(conn, batch_id)

    offset = get_pagination_offset(query.page, query.page_size)
    rows = await list_import_errors_by_batch_paginated(conn, batch_id, query.page_size, offset)

    return {
        "status": True,
        "message": "Erros de importacao carregados com sucesso.",
        "data": {
            "errors": rows,
            "pagination": build_pagination(query.page, query.page_size, total),
        },
    }
