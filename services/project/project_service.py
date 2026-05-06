from pathlib import Path
from typing import Optional
from uuid import uuid4

import asyncpg
from fastapi.encoders import jsonable_encoder

from core.config.config import (
    PROJECT_COVER_MAX_BYTES,
    PROJECT_COVER_PUBLIC_PATH,
    PROJECT_COVER_UPLOAD_DIR,
)
from core.logger.logger import logger
from functions.utils.utils import (
    build_pagination,
    extract_authenticated_user_context,
    service_response,
)
from schemas.project.project import ProjectListQueryRequest, ProjectManagedListQueryRequest, ProjectUpdateRequest
from schemas.project.project_image import ProjectLogoUploadRequest
from repositories.project.project_repository import (
    create_project_assignment,
    deactivate_project_assignment,
    exists_public_project,
    get_public_project_assignments,
    get_public_project_by_id,
    get_public_projects,
    get_user_managed_projects,
    update_managed_project_fields,
    upsert_project_cover_image,
)


ALLOWED_PROJECT_COVER_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _delete_project_cover_file(image_url: Optional[str]) -> None:
    if not image_url:
        return

    public_prefix = PROJECT_COVER_PUBLIC_PATH.strip("/").replace("\\", "/") + "/"
    normalized_url = image_url.replace("\\", "/")
    if not normalized_url.startswith(public_prefix):
        return

    filename = normalized_url.removeprefix(public_prefix)
    if "/" in filename or "\\" in filename:
        return

    file_path = Path(PROJECT_COVER_UPLOAD_DIR) / filename
    try:
        file_path.unlink(missing_ok=True)
    except OSError as e:
        logger.warning("Nao foi possivel remover capa antiga do projeto: %s", e)


async def list_projects(
    conn: asyncpg.Connection,
    query: ProjectListQueryRequest,
) -> dict:
    try:
        projects, total = await get_public_projects(
            conn=conn,
            area_ids=query.area_ids,
            unidade_ids=query.unidade_ids,
            curso_ids=query.curso_ids,
            ordenacao=query.ordenacao,
            page=query.page,
            page_size=query.page_size,
            somente_habilitados=query.somente_habilitados,
            q=query.q,
        )
        encoded_projects = jsonable_encoder(projects)

        pagination = build_pagination(query.page, query.page_size, total)

        if not encoded_projects:
            return service_response(
                True,
                "Nenhum projeto encontrado para os filtros informados.",
                data={
                    "projetos": [],
                    "paginacao": pagination,
                },
            )

        return service_response(
            True,
            "Projetos recuperados com sucesso.",
            data={
                "projetos": encoded_projects,
                "paginacao": pagination,
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


async def list_my_projects(
    conn: asyncpg.Connection,
    user: dict,
    query: ProjectManagedListQueryRequest,
) -> dict:
    try:
        auth_context = extract_authenticated_user_context(user)
        if not auth_context:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role = auth_context

        projects, total = await get_user_managed_projects(
            conn=conn,
            user_id=user_id,
            user_role=user_role,
            page=query.page,
            page_size=query.page_size,
            q=query.q,
        )
        encoded_projects = jsonable_encoder(projects)
        pagination = build_pagination(query.page, query.page_size, total)

        if not encoded_projects:
            return service_response(
                True,
                "Nenhum projeto encontrado para o usuario autenticado.",
                data={
                    "projetos": [],
                    "paginacao": pagination,
                },
            )

        return service_response(
            True,
            "Projetos do usuario recuperados com sucesso.",
            data={
                "projetos": encoded_projects,
                "paginacao": pagination,
            },
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao recuperar projetos do usuario.")


async def update_my_project(
    conn: asyncpg.Connection,
    user: dict,
    project_id: int,
    data: ProjectUpdateRequest,
) -> dict:
    try:
        if project_id <= 0:
            return service_response(False, "Projeto invalido.")

        auth_context = extract_authenticated_user_context(user)
        if not auth_context:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role = auth_context
        allowed_columns = {"descricao", "descricao_curta"}
        filtered = {k: v for k, v in data.model_dump(exclude_unset=True).items() if k in allowed_columns}

        if not filtered:
            return service_response(False, "Nenhum campo valido informado para atualizacao.")

        db_column_map = {
            "descricao": "full_description",
            "descricao_curta": "short_description",
        }

        allowed_fields = {
            db_column_map[field_name]: field_value
            for field_name, field_value in filtered.items()
        }

        updated_project = await update_managed_project_fields(
            conn=conn,
            project_id=project_id,
            user_id=user_id,
            user_role=user_role,
            allowed_fields=allowed_fields,
        )
        if not updated_project:
            return service_response(False, "Projeto nao encontrado ou sem permissao.")

        return service_response(
            True,
            "Projeto atualizado com sucesso.",
            data={"projeto": jsonable_encoder(updated_project)},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao atualizar projeto.")


async def upload_project_logo(
    conn: asyncpg.Connection,
    user: dict,
    project_id: int,
    data: ProjectLogoUploadRequest,
) -> dict:
    saved_file: Path | None = None
    try:
        if project_id <= 0:
            return service_response(False, "Projeto invalido.")

        auth_context = extract_authenticated_user_context(user)
        if not auth_context:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role = auth_context
        image = data.image
        content_type = (image.content_type or "").lower()
        extension = ALLOWED_PROJECT_COVER_TYPES.get(content_type)
        if not extension:
            return service_response(False, "Formato de imagem invalido. Use JPG, PNG, WEBP ou GIF.")

        contents = await image.read()
        if not contents:
            return service_response(False, "Imagem invalida.")

        if len(contents) > PROJECT_COVER_MAX_BYTES:
            return service_response(False, "Imagem muito grande. O tamanho maximo e 5MB.")

        upload_dir = Path(PROJECT_COVER_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4().hex}{extension}"
        saved_file = upload_dir / filename
        saved_file.write_bytes(contents)
        image_url = f"{PROJECT_COVER_PUBLIC_PATH.strip('/')}/{filename}"

        logo = await upsert_project_cover_image(
            conn=conn,
            project_id=project_id,
            user_id=user_id,
            user_role=user_role,
            image_url=image_url,
            alt_text=data.alt_text,
        )
        if not logo:
            saved_file.unlink(missing_ok=True)
            return service_response(False, "Projeto nao encontrado ou sem permissao.")

        _delete_project_cover_file(logo.get("previous_image_url"))

        return service_response(
            True,
            "Logo do projeto atualizada com sucesso.",
            data={"logo": jsonable_encoder(logo)},
        )
    except Exception as e:
        if saved_file:
            saved_file.unlink(missing_ok=True)
        logger.exception(e)
        return service_response(False, "Erro ao atualizar logo do projeto.")


async def create_my_project_assignment(
    conn: asyncpg.Connection,
    user: dict,
    project_id: int,
    descricao: str,
    curso_ids: list[int],
) -> dict:
    try:
        if project_id <= 0:
            return service_response(False, "Projeto invalido.")

        auth_context = extract_authenticated_user_context(user)
        if not auth_context:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role = auth_context
        if not descricao:
            return service_response(False, "Descricao da atribuicao invalida.")

        if not curso_ids:
            return service_response(False, "Informe ao menos um curso valido.")

        async with conn.transaction():
            assignment_result = await create_project_assignment(
                conn=conn,
                project_id=project_id,
                user_id=user_id,
                user_role=user_role,
                descricao=descricao,
                course_ids=curso_ids,
            )

            if not assignment_result["has_project_access"]:
                raise ValueError("Projeto nao encontrado ou sem permissao.")

            if assignment_result["valid_course_count"] != assignment_result["requested_course_count"]:
                raise ValueError("Todos os cursos devem estar vinculados ao projeto.")

            assignment = assignment_result.get("assignment")
            if not assignment:
                raise ValueError("Nao foi possivel criar a atribuicao.")

        return service_response(
            True,
            "Atribuicao criada com sucesso.",
            data={"atribuicao": jsonable_encoder(assignment)},
        )
    except ValueError as e:
        logger.exception(e)
        return service_response(False, str(e))
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao criar atribuicao do projeto.")


async def delete_my_project_assignment(
    conn: asyncpg.Connection,
    user: dict,
    assignment_id: int,
) -> dict:
    try:
        if assignment_id <= 0:
            return service_response(False, "Atribuicao invalida.")

        auth_context = extract_authenticated_user_context(user)
        if not auth_context:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role = auth_context
        removed = await deactivate_project_assignment(
            conn=conn,
            assignment_id=assignment_id,
            user_id=user_id,
            user_role=user_role,
        )
        if not removed:
            return service_response(False, "Atribuicao nao encontrada ou sem permissao.")

        return service_response(
            True,
            "Atribuicao removida com sucesso.",
            data={
                "atribuicao": {
                    "atribuicao_id": assignment_id,
                    "removida": True,
                }
            },
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao remover atribuicao do projeto.")
