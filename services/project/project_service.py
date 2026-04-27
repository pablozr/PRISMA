from math import ceil
from typing import Optional, cast

import asyncpg
from fastapi.encoders import jsonable_encoder

from core.config.config import (
    PROJECTS_ALLOWED_SORT_OPTIONS,
    PROJECTS_DEFAULT_PAGE,
    PROJECTS_DEFAULT_PAGE_SIZE,
    PROJECTS_DEFAULT_SORT,
    PROJECTS_MAX_PAGE_SIZE,
)
from core.logger.logger import logger
from functions.utils.utils import (
    get_safe_limit_offset,
    normalize_positive_int_list,
    service_response,
)
from repositories.project.project_repository import (
    ProjectSortOption,
    exists_public_project,
    get_public_project_assignments,
    get_public_project_by_id,
    get_public_projects,
)


async def list_projects(
    conn: asyncpg.Connection,
    area_ids: Optional[list[int]],
    unidade_ids: Optional[list[int]],
    curso_ids: Optional[list[int]],
    ordenacao: Optional[str],
    page: int,
    page_size: int,
    somente_habilitados: bool,
    q: Optional[str] = None,
) -> dict:
    try:
        sort_option = ordenacao or PROJECTS_DEFAULT_SORT
        if sort_option not in PROJECTS_ALLOWED_SORT_OPTIONS:
            return service_response(
                False,
                "Ordenacao invalida.",
            )


        safe_page = page if page > 0 else PROJECTS_DEFAULT_PAGE
        requested_page_size = page_size if page_size > 0 else PROJECTS_DEFAULT_PAGE_SIZE
        safe_page_size, _ = get_safe_limit_offset(
            limit=requested_page_size,
            offset=0,
            max_limit=PROJECTS_MAX_PAGE_SIZE,
            max_offset=0,
        )
        safe_area_ids = normalize_positive_int_list(area_ids)
        safe_unidade_ids = normalize_positive_int_list(unidade_ids)
        safe_curso_ids = normalize_positive_int_list(curso_ids)

        projects, total = await get_public_projects(
            conn=conn,
            area_ids=safe_area_ids,
            unidade_ids=safe_unidade_ids,
            curso_ids=safe_curso_ids,
            ordenacao=sort_option,
            page=safe_page,
            page_size=safe_page_size,
            somente_habilitados=somente_habilitados,
            q=q,
        )
        encoded_projects = jsonable_encoder(projects)

        total_pages = ceil(total / safe_page_size) if total > 0 else 0

        if not encoded_projects:
            return service_response(
                True,
                "Nenhum projeto encontrado para os filtros informados.",
                data={
                    "projetos": [],
                    "paginacao": {
                        "page": safe_page,
                        "page_size": safe_page_size,
                        "total": total,
                        "total_pages": total_pages,
                    },
                },
            )

        return service_response(
            True,
            "Projetos recuperados com sucesso.",
            data={
                "projetos": encoded_projects,
                "paginacao": {
                    "page": safe_page,
                    "page_size": safe_page_size,
                    "total": total,
                    "total_pages": total_pages,
                },
            },
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao recuperar projetos.")


async def get_project_detail(conn: asyncpg.Connection, project_id: int) -> dict:
    try:
        if project_id <= 0:
            return service_response(False, "Projeto invalido.")

        project = await get_public_project_by_id(conn, project_id)
        if not project:
            return service_response(False, "Projeto nao encontrado.")

        encoded_project = jsonable_encoder(project)

        return service_response(True, "Detalhes do projeto recuperados com sucesso.", data={"projeto": encoded_project})
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao recuperar projeto.")


async def list_project_assignments(conn: asyncpg.Connection, project_id: int) -> dict:
    try:
        if project_id <= 0:
            return service_response(False, "Projeto invalido.")

        assignments = await get_public_project_assignments(conn, project_id)

        if not assignments:
            project_exists = await exists_public_project(conn, project_id)
            if not project_exists:
                return service_response(False, "Projeto nao encontrado.")

            return service_response(
                True,
                "Projeto sem atribuicoes cadastradas.",
                data={"atribuicoes": []},
            )

        encoded_assignments = jsonable_encoder(assignments)

        return service_response(
            True,
            "Atribuicoes do projeto recuperadas com sucesso.",
            data={"atribuicoes": encoded_assignments},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao recuperar atribuicoes do projeto.")
