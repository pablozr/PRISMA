from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.config.config import PROJECTS_DEFAULT_PAGE, PROJECTS_DEFAULT_PAGE_SIZE
from core.postgresql.postgresql import postgresql
from core.security import security
from functions.utils.utils import default_response
from schemas.project.project import ProjectUpdateRequest
from schemas.project.project_image import ProjectLogoUploadRequest
from services.project.project_service import (
    list_my_projects,
    update_my_project,
    upload_project_logo,
)

router = APIRouter()


@router.get("/me/projetos")
async def get_my_projects(
    user=Depends(security.require_student_rank()),
    conn=Depends(postgresql.get_db),
    page: int = PROJECTS_DEFAULT_PAGE,
    page_size: int = PROJECTS_DEFAULT_PAGE_SIZE,
    q: Optional[str] = Query(default=None),
):
    return await default_response(list_my_projects, [conn, user, page, page_size, q])


@router.patch("/projetos/{project_id}")
async def patch_my_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    user=Depends(security.require_student_rank()),
    conn=Depends(postgresql.get_db),
):
    return await default_response(
        update_my_project,
        [conn, user, project_id, payload.titulo, payload.descricao],
    )


@router.post("/projetos/{project_id}/logo")
async def post_project_logo(
    project_id: int,
    payload: ProjectLogoUploadRequest,
    user=Depends(security.require_student_rank()),
    conn=Depends(postgresql.get_db),
):
    return await default_response(
        upload_project_logo,
        [conn, user, project_id, payload.image_url, payload.alt_text],
    )
