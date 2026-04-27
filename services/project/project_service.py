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
    get_managed_project_by_id,
    get_public_project_assignments,
    get_public_project_by_id,
    get_public_projects,
    get_user_managed_projects,
    update_managed_project_fields,
    upsert_project_cover_image,
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


def _extract_authenticated_user_context(user: dict) -> tuple[int, str, str] | None:
    user_id = user.get("id")
    user_role = user.get("role")
    user_email = user.get("institutional_email") or user.get("email")

    if not isinstance(user_id, int) or user_id <= 0:
        return None

    if not isinstance(user_role, str) or not user_role.strip():
        return None

    if not isinstance(user_email, str) or not user_email.strip():
        return None

    return user_id, user_role.strip().lower(), user_email.strip()


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    normalized = value.strip()
    return normalized if normalized else None


async def list_my_projects(
    conn: asyncpg.Connection,
    user: dict,
    page: int,
    page_size: int,
    q: Optional[str] = None,
) -> dict:
    try:
        auth_context = _extract_authenticated_user_context(user)
        if not auth_context:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role, user_email = auth_context

        safe_page = page if page > 0 else PROJECTS_DEFAULT_PAGE
        requested_page_size = page_size if page_size > 0 else PROJECTS_DEFAULT_PAGE_SIZE
        safe_page_size, _ = get_safe_limit_offset(
            limit=requested_page_size,
            offset=0,
            max_limit=PROJECTS_MAX_PAGE_SIZE,
            max_offset=0,
        )

        projects, total = await get_user_managed_projects(
            conn=conn,
            user_id=user_id,
            user_role=user_role,
            user_email=user_email,
            page=safe_page,
            page_size=safe_page_size,
            q=q,
        )
        encoded_projects = jsonable_encoder(projects)
        total_pages = ceil(total / safe_page_size) if total > 0 else 0

        if not encoded_projects:
            return service_response(
                True,
                "Nenhum projeto encontrado para o usuario autenticado.",
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
            "Projetos do usuario recuperados com sucesso.",
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
        return service_response(False, "Erro ao recuperar projetos do usuario.")


async def update_my_project(
    conn: asyncpg.Connection,
    user: dict,
    project_id: int,
    titulo: Optional[str],
    descricao: Optional[str],
) -> dict:
    try:
        if project_id <= 0:
            return service_response(False, "Projeto invalido.")

        auth_context = _extract_authenticated_user_context(user)
        if not auth_context:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role, user_email = auth_context
        safe_titulo = _normalize_optional_text(titulo)
        safe_descricao = _normalize_optional_text(descricao)

        if titulo is not None and safe_titulo is None:
            return service_response(False, "Titulo invalido.")

        if descricao is not None and safe_descricao is None:
            return service_response(False, "Descricao invalida.")

        if safe_titulo is None and safe_descricao is None:
            return service_response(False, "Informe titulo ou descricao para atualizar.")

        managed_project = await get_managed_project_by_id(
            conn=conn,
            project_id=project_id,
            user_id=user_id,
            user_role=user_role,
            user_email=user_email,
        )
        if not managed_project:
            return service_response(False, "Projeto nao encontrado ou sem permissao.")

        updated = await update_managed_project_fields(
            conn=conn,
            project_id=project_id,
            titulo=safe_titulo,
            descricao=safe_descricao,
        )
        if not updated:
            return service_response(False, "Nao foi possivel atualizar o projeto.")

        refreshed_project = await get_managed_project_by_id(
            conn=conn,
            project_id=project_id,
            user_id=user_id,
            user_role=user_role,
            user_email=user_email,
        )
        encoded_project = jsonable_encoder(refreshed_project or managed_project)

        return service_response(
            True,
            "Projeto atualizado com sucesso.",
            data={"projeto": encoded_project},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao atualizar projeto.")


async def upload_project_logo(
    conn: asyncpg.Connection,
    user: dict,
    project_id: int,
    image_url: str,
    alt_text: Optional[str],
) -> dict:
    try:
        if project_id <= 0:
            return service_response(False, "Projeto invalido.")

        auth_context = _extract_authenticated_user_context(user)
        if not auth_context:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role, user_email = auth_context
        safe_image_url = image_url.strip()
        if not safe_image_url:
            return service_response(False, "URL da imagem invalida.")

        safe_alt_text = _normalize_optional_text(alt_text)
        managed_project = await get_managed_project_by_id(
            conn=conn,
            project_id=project_id,
            user_id=user_id,
            user_role=user_role,
            user_email=user_email,
        )
        if not managed_project:
            return service_response(False, "Projeto nao encontrado ou sem permissao.")

        logo = await upsert_project_cover_image(
            conn=conn,
            project_id=project_id,
            image_url=safe_image_url,
            alt_text=safe_alt_text,
        )
        if not logo:
            return service_response(False, "Nao foi possivel atualizar a logo do projeto.")

        return service_response(
            True,
            "Logo do projeto atualizada com sucesso.",
            data={"logo": jsonable_encoder(logo)},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao atualizar logo do projeto.")
