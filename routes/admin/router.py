from fastapi import APIRouter, Depends

from core.postgresql.postgresql import postgresql
from core.security import security
from functions.utils.utils import default_response
from schemas.admin import AdminUserUpdateRequest, AdminUsersListQuery
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
