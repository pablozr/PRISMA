from fastapi import APIRouter, Depends

from core.postgresql.postgresql import postgresql
from core.security import security
from functions.utils.utils import default_response
from schemas.admin import (
    AdminSyncRunErrorsListQuery,
    AdminSyncRunsListQuery,
    AdminProjectUpdateRequest,
    AdminProjectsListQuery,
    AdminUserUpdateRequest,
    AdminUsersListQuery,
)
from services.admin import admin_service

router = APIRouter()


@router.get("/metrics")
async def get_admin_metrics(
    _=Depends(security.require_admin_rank()),
    conn=Depends(postgresql.get_db),
):
    return await default_response(admin_service.get_dashboard_metrics, [conn])


@router.get("/users")
async def get_admin_users(
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    _=Depends(security.require_admin_rank()),
    conn=Depends(postgresql.get_db),
):
    query = AdminUsersListQuery(page=page, page_size=page_size, q=q)
    return await default_response(admin_service.list_users, [conn, query])


@router.patch("/users/{user_id}")
async def patch_admin_user(
    user_id: int,
    payload: AdminUserUpdateRequest,
    _=Depends(security.require_admin_rank()),
    conn=Depends(postgresql.get_db),
):
    return await default_response(admin_service.update_user, [conn, user_id, payload])


@router.get("/projects")
async def get_admin_projects(
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    _=Depends(security.require_admin_rank()),
    conn=Depends(postgresql.get_db),
):
    query = AdminProjectsListQuery(page=page, page_size=page_size, q=q)
    return await default_response(admin_service.list_projects, [conn, query])


@router.patch("/projects/{project_id}")
async def patch_admin_project(
    project_id: int,
    payload: AdminProjectUpdateRequest,
    _=Depends(security.require_admin_rank()),
    conn=Depends(postgresql.get_db),
):
    return await default_response(admin_service.update_project, [conn, project_id, payload])


@router.get("/sync-runs")
async def get_admin_sync_runs(
    page: int = 1,
    page_size: int = 20,
    _=Depends(security.require_admin_rank()),
    conn=Depends(postgresql.get_db),
):
    query = AdminSyncRunsListQuery(page=page, page_size=page_size)
    return await default_response(admin_service.list_sync_runs, [conn, query])


@router.get("/sync-runs/{sync_run_id}/failures")
async def get_admin_sync_run_failures(
    sync_run_id: int,
    page: int = 1,
    page_size: int = 20,
    _=Depends(security.require_admin_rank()),
    conn=Depends(postgresql.get_db),
):
    query = AdminSyncRunErrorsListQuery(page=page, page_size=page_size)
    return await default_response(admin_service.list_sync_run_failures, [conn, sync_run_id, query])
