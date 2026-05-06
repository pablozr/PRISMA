from functions.utils.utils import service_response
from repositories.user.user_repository import get_active_user_by_id


async def get_one_user(conn, user_id: int) -> dict:
    row = await get_active_user_by_id(conn, user_id)

    if not row:
        return service_response(status=False, message="Usuario nao encontrado")

    return service_response(status=True, message="Usuario recuperado com sucesso", data={"user": row})
