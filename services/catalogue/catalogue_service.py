import asyncpg
from repositories.catalogue.catalogue_repository import (
    get_all_areas_tematicas,
    get_all_centros,
    get_all_cursos,
    get_all_unidades,
)
from functions.utils.utils import service_response
from core.logger.logger import logger
from schemas.catalogue.catalogue import (
    CatalogueCoursesQueryRequest,
    CataloguePaginationQueryRequest,
    CatalogueUnitsQueryRequest,
)

async def get_areas_tematicas(conn: asyncpg.Connection, query: CataloguePaginationQueryRequest) -> dict:
    try:
        areas = await get_all_areas_tematicas(conn, limit=query.limit, offset=query.offset)

        return service_response(True, "Áreas temáticas recuperadas com sucesso", True, areas)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar áreas temáticas", True, [])


async def get_centros(conn: asyncpg.Connection, query: CataloguePaginationQueryRequest) -> dict:
    try:
        centros = await get_all_centros(conn, limit=query.limit, offset=query.offset)

        return service_response(True, "Centros recuperados com sucesso", True, centros)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar centros", True, [])


async def get_unidades(
    conn: asyncpg.Connection,
    query: CatalogueUnitsQueryRequest,
) -> dict:
    try:
        unidades = await get_all_unidades(
            conn,
            centro_ids=query.centro_ids,
            limit=query.limit,
            offset=query.offset,
        )

        return service_response(True, "Unidades recuperadas com sucesso", True, unidades)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar institutos/escolas", True, [])


async def get_cursos(
    conn: asyncpg.Connection,
    query: CatalogueCoursesQueryRequest,
) -> dict:
    try:
        cursos = await get_all_cursos(
            conn,
            unidade_ids=query.unidade_ids,
            limit=query.limit,
            offset=query.offset,
        )

        return service_response(True, "Cursos recuperados com sucesso", True, cursos)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar cursos", True, [])
