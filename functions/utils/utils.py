from typing import Callable, List, Any
import inspect
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
            return JSONResponse(status_code=status_code, content={"message": result["message"], "data": result["data"]})
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
