import csv
import hashlib
from datetime import datetime
from io import StringIO

from fastapi import UploadFile

from schemas.admin import (
    AdminImportErrorsListQuery,
    AdminImportsListQuery,
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

    query = """
        INSERT INTO import_batches (
            reference_year,
            reference_term,
            uploaded_by_user_id,
            source_filename,
            source_hash,
            status,
            total_rows,
            imported_rows,
            rejected_rows,
            created_at,
            finished_at
        )
        VALUES ($1, $2, $3, $4, $5, 'success', $6, $6, 0, NOW(), NOW())
        RETURNING id, status, total_rows, imported_rows, rejected_rows, created_at, finished_at;
    """
    row = await conn.fetchrow(
        query,
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
    count_query = "SELECT COUNT(*)::BIGINT AS total FROM import_batches;"
    count_row = await conn.fetchrow(count_query)
    total = int(count_row["total"]) if count_row else 0

    offset = (query.page - 1) * query.page_size
    list_query = """
        SELECT
            ib.id,
            ib.reference_year,
            ib.reference_term,
            ib.source_filename,
            ib.source_hash,
            ib.status,
            ib.total_rows,
            ib.imported_rows,
            ib.rejected_rows,
            ib.created_at,
            ib.finished_at,
            u.id AS uploaded_by_user_id,
            u.full_name AS uploaded_by_name,
            u.institutional_email::TEXT AS uploaded_by_email
        FROM import_batches ib
        LEFT JOIN users u ON u.id = ib.uploaded_by_user_id
        ORDER BY ib.created_at DESC, ib.id DESC
        LIMIT $1
        OFFSET $2;
    """
    rows = await conn.fetch(list_query, query.page_size, offset)
    total_pages = (total + query.page_size - 1) // query.page_size if total else 0

    return {
        "status": True,
        "message": "Historico de importacoes carregado com sucesso.",
        "data": {
            "batches": [{**row} for row in rows],
            "pagination": {
                "page": query.page,
                "page_size": query.page_size,
                "total": total,
                "total_pages": total_pages,
            },
        },
    }


async def list_import_errors(conn, batch_id: int, query: AdminImportErrorsListQuery) -> dict:
    count_query = "SELECT COUNT(*)::BIGINT AS total FROM import_row_errors WHERE import_batch_id = $1;"
    count_row = await conn.fetchrow(count_query, batch_id)
    total = int(count_row["total"]) if count_row else 0

    offset = (query.page - 1) * query.page_size
    list_query = """
        SELECT id, import_batch_id, row_number, raw_payload, error_reason, created_at
        FROM import_row_errors
        WHERE import_batch_id = $1
        ORDER BY row_number ASC, id ASC
        LIMIT $2
        OFFSET $3;
    """
    rows = await conn.fetch(list_query, batch_id, query.page_size, offset)
    total_pages = (total + query.page_size - 1) // query.page_size if total else 0

    return {
        "status": True,
        "message": "Erros de importacao carregados com sucesso.",
        "data": {
            "errors": [{**row} for row in rows],
            "pagination": {
                "page": query.page,
                "page_size": query.page_size,
                "total": total,
                "total_pages": total_pages,
            },
        },
    }
