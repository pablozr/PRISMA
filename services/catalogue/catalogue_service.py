import asyncpg
from repositories.catalogue.catalogue_repository import get_all_areas_tematicas, get_all_centros
from functions.utils.utils import service_response
from core.logger.logger import logger

async def get_areas_tematicas(conn: asyncpg.Connection, limit: int, offset: int) -> dict:
    try:
        safe_limit = max(1, min(limit, 100))
        safe_offset = offset - safe_limit

        areas = await get_all_areas_tematicas(conn, limit=safe_limit, offset=safe_offset)

        if not areas:
            return service_response(False, "Sem áreas temáticas disponíveis", True, [])

        return service_response(True, "Áreas temáticas recuperadas com sucesso", True, areas)
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar áreas temáticas", True, [])


async def get_centros(conn: asyncpg.Connection, limit: int, offset: int) -> dict:
    try:

        return service_response(True, "Centros recuperados com sucesso", True, [])
    except Exception as e:
        logger.error(e)
        return service_response(False, "Erro ao recuperar centros", True, [])