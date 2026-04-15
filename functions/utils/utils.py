from typing import Callable
import inspect
from starlette.responses import JSONResponse
from core.logger.logger import logger


async def default_response(callable_function: Callable, params: list = [], is_creation: bool = False, dict_response: bool = False):
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


def is_async_callable(fn: Callable) -> bool:
    return inspect.iscoroutinefunction(fn)