from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from core.config.config import (
    PROJECTS_DEFAULT_PAGE,
    PROJECTS_DEFAULT_PAGE_SIZE,
    PROJECTS_DEFAULT_ONLY_ENABLED,
    PROJECTS_DEFAULT_SORT,
)
from core.postgresql.postgresql import postgresql
from functions.utils.utils import default_response
from services.project.project_service import (
    get_project_detail,
    list_project_assignments,
    list_projects,
)

router = APIRouter()


@router.get("")
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
            area_ids,
            unidade_ids,
            curso_ids,
            ordenacao,
            page,
            page_size,
            somente_habilitados,
            q,
        ],
    )


@router.get("/{project_id}")
async def get_project_by_id(project_id: int, conn=Depends(postgresql.get_db)):
    return await default_response(get_project_detail, [conn, project_id])


@router.get("/{project_id}/atribuicoes")
async def get_project_assignments(project_id: int, conn=Depends(postgresql.get_db)):
    return await default_response(list_project_assignments, [conn, project_id])
