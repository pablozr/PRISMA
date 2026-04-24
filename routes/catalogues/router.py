from typing import Optional, List

from fastapi import APIRouter, Depends

from functions.utils.utils import default_response
from core.postgresql.postgresql import postgresql
from services.catalogue.catalogue_service import get_areas_tematicas

router = APIRouter()

@router.get("/areas-tematicas")
async def get_areas_tematicas(conn = Depends(postgresql.get_db), limit: int = 50, offset: int = 0):
    return default_response(get_areas_tematicas, [conn, limit, offset])


@router.get("/centros")
async def get_centros():
    return default_response(lambda: None, dict_response=True)


@router.get("/unidades")
async def get_unidades(centros_ids: Optional[List[str]] = None):
    return default_response(lambda: None, dict_response=True)


@router.get("/cursos")
async def get_cursos(unidades_ids: Optional[List[str]] = None):
    return default_response(lambda: None, dict_response=True)