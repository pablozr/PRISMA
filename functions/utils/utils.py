from typing import Any, Callable, List, Optional
import inspect
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from core.logger.logger import logger


async def default_response(callable_function: Callable, params: list = [], is_creation: bool = False,
                           dict_response: bool = False):
    try:
        if is_async_callable(callable_function):
            result = await callable_function(*params)
        else:
            result = callable_function(*params)
        if not result["status"]:
            if not dict_response:
                return JSONResponse(status_code=400, content={"detail": result["message"]})
            return {"status": False, "message": result["message"]}

        status_code = 200 if not is_creation else 201
        if not dict_response:
            payload = jsonable_encoder({"message": result["message"], "data": result["data"]})
            return JSONResponse(status_code=status_code, content=payload)
        return {"status": True, "message": result["message"], "data": result["data"]}
    except Exception as e:
        logger.exception(e)
        if not dict_response:
            return JSONResponse(status_code=500, content={"detail": "Erro interno com o servidor."})
        return {"status": False, "message": "Erro interno com o servidor."}


def service_response(status: bool, message: str,is_list: bool = None, data: dict | List[Any] = None) -> dict:
    return {"status": status, "message": message, "data": data or ([] if is_list else {})}


def is_async_callable(fn: Callable) -> bool:
    return inspect.iscoroutinefunction(fn)


def get_safe_limit_offset(limit: int, offset: int, max_limit: int = 100, max_offset: int = 1000) -> tuple[int, int]:
    safe_limit = max(1, min(limit, max_limit))
    safe_offset = max(0, min(offset, max_offset))
    return safe_limit, safe_offset


def normalize_positive_int_list(values: Optional[list[int]]) -> Optional[list[int]]:
    if not values:
        return None

    normalized = sorted({value for value in values if isinstance(value, int) and value > 0})
    return normalized or None


def extract_authenticated_user_context(user: dict) -> tuple[int, str] | None:
    user_id = user.get("id")
    user_role = user.get("role")

    if not isinstance(user_id, int) or user_id <= 0:
        return None

    if not isinstance(user_role, str) or not user_role.strip():
        return None

    return user_id, user_role.strip().lower()


def extract_user_identity(user: dict) -> tuple[int, str, str]:
    user_id = user.get("id")
    email = user.get("email") or user.get("institutional_email")
    role = user.get("role")

    if user_id is None or not email or not role:
        raise ValueError("Invalid user identity")

    return user_id, email, role


def build_login_success_response(access_token: str, refresh_token: str) -> dict:
    return service_response(
        status=True,
        message="Login successful",
        data={"accessToken": access_token, "refreshToken": refresh_token},
    )
