from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from core.config.config import (
    PROJECTS_DEFAULT_PAGE,
    PROJECTS_DEFAULT_PAGE_SIZE,
    PROJECTS_DEFAULT_ONLY_ENABLED,
    PROJECTS_DEFAULT_SORT,
)
from core.postgresql.postgresql import postgresql
from core.security import security
from functions.utils.utils import default_response
from schemas.project.project import (
    ProjectUpdateRequest,
    build_project_list_query_request,
    build_project_managed_list_query_request,
)
from schemas.project.project_assignment import ProjectAssignmentCreateRequest
from schemas.project.project_image import ProjectLogoUploadRequest
from services.project.project_service import (
    create_my_project_assignment,
    delete_my_project_assignment,
    get_project_detail,
    list_my_projects,
    list_project_assignments,
    list_projects,
    update_my_project,
    upload_project_logo,
)

router = APIRouter()


@router.get("/projects")
async def get_projects(
    conn=Depends(postgresql.get_db),
    q: Optional[str] = None,
    area_ids: Optional[List[int]] = Query(default=None),
    unidade_ids: Optional[List[int]] = Query(default=None),
    curso_ids: Optional[List[int]] = Query(default=None),
    ordenacao: str = PROJECTS_DEFAULT_SORT,
    page: int = PROJECTS_DEFAULT_PAGE,
    page_size: int = PROJECTS_DEFAULT_PAGE_SIZE,
    somente_habilitados: bool = PROJECTS_DEFAULT_ONLY_ENABLED,
):
    return await default_response(
        list_projects,
        [
            conn,
            build_project_list_query_request(
                q=q,
                area_ids=area_ids,
                unidade_ids=unidade_ids,
                curso_ids=curso_ids,
                ordenacao=ordenacao,
                page=page,
                page_size=page_size,
                somente_habilitados=somente_habilitados,
            ),
        ],
    )


@router.get("/projects/{project_id}")
async def get_project_by_id(project_id: int, conn=Depends(postgresql.get_db)):
    return await default_response(get_project_detail, [conn, project_id])


@router.get("/projects/{project_id}/atribuicoes")
async def get_project_assignments(project_id: int, conn=Depends(postgresql.get_db)):
    return await default_response(list_project_assignments, [conn, project_id])


@router.get("/me/projects")
async def get_my_projects(
    user=Depends(security.require_manager_rank()),
    conn=Depends(postgresql.get_db),
    page: int = PROJECTS_DEFAULT_PAGE,
    page_size: int = PROJECTS_DEFAULT_PAGE_SIZE,
    q: Optional[str] = Query(default=None),
):
    query = build_project_managed_list_query_request(q=q, page=page, page_size=page_size)
    return await default_response(list_my_projects, [conn, user, query])


@router.patch("/projects/{project_id}")
async def patch_my_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    user=Depends(security.require_manager_rank()),
    conn=Depends(postgresql.get_db),
):
    return await default_response(
        update_my_project,
        [conn, user, project_id, payload],
    )


@router.post("/projects/{project_id}/logo")
async def post_project_logo(
    project_id: int,
    image: UploadFile = File(...),
    alt_text: Optional[str] = Form(default=None),
    user=Depends(security.require_manager_rank()),
    conn=Depends(postgresql.get_db),
):
    payload = ProjectLogoUploadRequest(image=image, alt_text=alt_text)
    return await default_response(
        upload_project_logo,
        [conn, user, project_id, payload],
    )


@router.post("/projects/{project_id}/atribuicoes")
async def post_project_assignment(
    project_id: int,
    payload: ProjectAssignmentCreateRequest,
    user=Depends(security.require_manager_rank()),
    conn=Depends(postgresql.get_db),
):
    return await default_response(
        create_my_project_assignment,
        [conn, user, project_id, payload.descricao, payload.curso_ids],
        is_creation=True,
    )


@router.delete("/atribuicoes/{assignment_id}")
async def delete_project_assignment(
    assignment_id: int,
    user=Depends(security.require_manager_rank()),
    conn=Depends(postgresql.get_db),
):
    return await default_response(delete_my_project_assignment, [conn, user, assignment_id])
