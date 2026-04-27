from typing import Optional, List

from fastapi import APIRouter, Depends

from functions.utils.utils import default_response
from core.postgresql.postgresql import postgresql
from services.catalogue.catalogue_service import (
    get_areas_tematicas as service_get_areas_tematicas,
    get_centros as service_get_centros,
)

router = APIRouter()

@router.get("/areas-tematicas")
async def list_areas_tematicas(conn = Depends(postgresql.get_db), limit: int = 50, offset: int = 0):
    return await default_response(service_get_areas_tematicas, [conn, limit, offset])


@router.get("/centros")
async def list_centros(conn = Depends(postgresql.get_db), limit: int = 50, offset: int = 0):
    return await default_response(service_get_centros, [conn, limit, offset])


@router.get("/unidades")
async def get_unidades(centros_ids: Optional[List[str]] = None):
    return await default_response(lambda: None, dict_response=True)


@router.get("/cursos")
async def get_cursos(unidades_ids: Optional[List[str]] = None):
    return await default_response(lambda: None, dict_response=True)
