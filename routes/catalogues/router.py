from typing import Optional

from fastapi import APIRouter, Depends, Query

from functions.utils.utils import default_response
from core.postgresql.postgresql import postgresql
from services.catalogue.catalogue_service import (
    get_areas_tematicas as service_get_areas_tematicas,
    get_cursos as service_get_cursos,
    get_centros as service_get_centros,
    get_unidades as service_get_unidades,
)

router = APIRouter()

@router.get("/areas-tematicas")
async def list_areas_tematicas(conn = Depends(postgresql.get_db), limit: int = 50, offset: int = 0):
    return await default_response(service_get_areas_tematicas, [conn, limit, offset])


@router.get("/centros")
async def list_centros(conn = Depends(postgresql.get_db), limit: int = 50, offset: int = 0):
    return await default_response(service_get_centros, [conn, limit, offset])


@router.get("/unidades")
async def list_unidades(
    conn=Depends(postgresql.get_db),
    centro_ids: Optional[list[int]] = Query(default=None),
    limit: int = 50,
    offset: int = 0,
):
    return await default_response(service_get_unidades, [conn, centro_ids, limit, offset])


@router.get("/cursos")
async def list_cursos(
    conn=Depends(postgresql.get_db),
    unidade_ids: Optional[list[int]] = Query(default=None),
    limit: int = 50,
    offset: int = 0,
):
    return await default_response(service_get_cursos, [conn, unidade_ids, limit, offset])
