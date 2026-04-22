from fastapi import APIRouter, Depends

from core.postgresql.postgresql import postgresql
from core.security import security
from functions.utils.utils import default_response
from services.user import user_service

router = APIRouter()


@router.get("/me")
async def get_me(
    user=Depends(security.validate_token_wrapper),
    conn=Depends(postgresql.get_db)
):
    user_id = user["userId"]
    return await default_response(
        user_service.get_one_user,
        [conn, user_id]
    )