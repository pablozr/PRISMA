import asyncpg
from repositories.catalogue.catalogue_repository import (
    get_all_areas_tematicas,
    get_all_centros,
    get_all_cursos,
    get_all_unidades,
)
from functions.utils.utils import service_response, get_safe_limit_offset, normalize_positive_int_list
from core.logger.logger import logger

async def get_areas_tematicas(conn: asyncpg.Connection, limit: int, offset: int) -> dict:
    try:
        safe_limit, safe_offset = get_safe_limit_offset(limit, offset)

        areas = await get_all_areas_tematicas(conn, limit=safe_limit, offset=safe_offset)

        if not areas:
            return service_response(False, "Sem áreas temáticas disponíveis", True, [])

        return service_response(True, "Áreas temáticas recuperadas com sucesso", True, areas)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar áreas temáticas", True, [])


async def get_centros(conn: asyncpg.Connection, limit: int, offset: int) -> dict:
    try:
        safe_limit, safe_offset = get_safe_limit_offset(limit, offset)

        centros = await get_all_centros(conn, limit=safe_limit, offset=safe_offset)

        if not centros:
            return service_response(False, "Sem centros disponíveis", True, [])

        return service_response(True, "Centros recuperados com sucesso", True, centros)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar centros", True, [])


async def get_unidades(
    conn: asyncpg.Connection,
    centro_ids: list[int] | None,
    limit: int,
    offset: int,
) -> dict:
    try:
        safe_limit, safe_offset = get_safe_limit_offset(limit, offset)
        normalized_centro_ids = normalize_positive_int_list(centro_ids)

        unidades = await get_all_unidades(
            conn,
            centro_ids=normalized_centro_ids,
            limit=safe_limit,
            offset=safe_offset,
        )

        if not unidades:
            return service_response(False, "Sem institutos/escolas disponíveis", True, [])

        return service_response(True, "Institutos/escolas recuperados com sucesso", True, unidades)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar institutos/escolas", True, [])


async def get_cursos(
    conn: asyncpg.Connection,
    unidade_ids: list[int] | None,
    limit: int,
    offset: int,
) -> dict:
    try:
        safe_limit, safe_offset = get_safe_limit_offset(limit, offset)
        normalized_unidade_ids = normalize_positive_int_list(unidade_ids)

        cursos = await get_all_cursos(
            conn,
            unidade_ids=normalized_unidade_ids,
            limit=safe_limit,
            offset=safe_offset,
        )

        if not cursos:
            return service_response(False, "Sem cursos disponíveis", True, [])

        return service_response(True, "Cursos recuperados com sucesso", True, cursos)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar cursos", True, [])
