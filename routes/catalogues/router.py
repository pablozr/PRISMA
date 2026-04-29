from typing import Optional

from fastapi import APIRouter, Depends, Query

from functions.utils.utils import default_response
from core.postgresql.postgresql import postgresql
from schemas.catalogue.catalogue import (
    build_catalogue_courses_query_request,
    build_catalogue_pagination_query_request,
    build_catalogue_units_query_request,
)
from services.catalogue.catalogue_service import (
    get_areas_tematicas as service_get_areas_tematicas,
    get_cursos as service_get_cursos,
    get_centros as service_get_centros,
    get_unidades as service_get_unidades,
)

router = APIRouter()

@router.get("/areas-tematicas")
async def list_areas_tematicas(conn = Depends(postgresql.get_db), limit: int = 50, offset: int = 0):
    query = build_catalogue_pagination_query_request(limit=limit, offset=offset)
    return await default_response(service_get_areas_tematicas, [conn, query])


@router.get("/centros")
async def list_centros(conn = Depends(postgresql.get_db), limit: int = 50, offset: int = 0):
    query = build_catalogue_pagination_query_request(limit=limit, offset=offset)
    return await default_response(service_get_centros, [conn, query])


@router.get("/unidades")
async def list_unidades(
    conn=Depends(postgresql.get_db),
    centro_ids: Optional[list[int]] = Query(default=None),
    limit: int = 50,
    offset: int = 0,
):
    query = build_catalogue_units_query_request(centro_ids=centro_ids, limit=limit, offset=offset)
    return await default_response(service_get_unidades, [conn, query])


@router.get("/cursos")
async def list_cursos(
    conn=Depends(postgresql.get_db),
    unidade_ids: Optional[list[int]] = Query(default=None),
    limit: int = 50,
    offset: int = 0,
):
    query = build_catalogue_courses_query_request(unidade_ids=unidade_ids, limit=limit, offset=offset)
    return await default_response(service_get_cursos, [conn, query])
