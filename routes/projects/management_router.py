from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.config.config import PROJECTS_DEFAULT_PAGE, PROJECTS_DEFAULT_PAGE_SIZE
from core.postgresql.postgresql import postgresql
from core.security import security
from functions.utils.utils import default_response
from services.project.project_service import list_my_projects

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
