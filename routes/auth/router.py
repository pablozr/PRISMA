import asyncpg
import redis
from fastapi import APIRouter, Request, Depends
from starlette.responses import JSONResponse

from core.config.config import COOKIE_AUTH_RESET
from core.postgresql.postgresql import postgresql
from core.rabbitmq.rabbitmq import rabbitmq
from core.redis.redis_cache import redis_cache
from core.security import security
from core.security.rate_limit import LOGIN_RATE_LIMIT_DEPS, VALIDATE_CODE_RATE_LIMIT_DEPS, \
    FORGET_PASSWORD_RATE_LIMIT_DEPS
from core.security.security import validate_token_refresh, validate_token_wrapper
from schemas.auth.auth import UserLoginRequest
from services.auth import auth_service
from services.auth.auth_service import login as auth_login, logout as auth_logout, refresh_token as auth_refresh

router = APIRouter()


@router.post("/login", dependencies=LOGIN_RATE_LIMIT_DEPS)
async def login(data: UserLoginRequest, conn=Depends(postgresql.get_db), redis_client=Depends(redis_cache.get_redis)):
    response = await auth_login(conn, redis_client, data)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    access_token = response["data"].pop("accessToken")
    refresh_token = response["data"].pop("refreshToken")

    resp = JSONResponse(status_code=200, content={"message": response["message"], "data": response["data"]})
    resp.set_cookie(
        key="COOKIE_AUTH",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=900
    )

    resp.set_cookie(
        key="COOKIE_REFRESH",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=604800,
    )

    return resp


@router.post("/logout", dependencies=[Depends(validate_token_wrapper)])
async def logout(request: Request, redis_client=Depends(redis_cache.get_redis)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return JSONResponse(status_code=400, content={"detail": "Session ID cookie is missing"})

    response = await auth_logout(redis_client, session_id)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    resp = JSONResponse(status_code=200, content={"message": response["message"]})
    resp.delete_cookie("COOKIE_AUTH", path="/", samesite="lax")
    resp.delete_cookie("COOKIE_REFRESH", path="/", samesite="lax")

    return resp


@router.post("/refresh", dependencies=[*LOGIN_RATE_LIMIT_DEPS, Depends(validate_token_refresh)])
async def refresh_token(request: Request, redis_client=Depends(redis_cache.get_redis)):
    response = await auth_refresh(redis_client, request.state.token)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    access_token = response["data"].pop("accessToken")
    refresh_token = response["data"].pop("refreshToken")

    resp = JSONResponse(status_code=200, content={"message": response["message"], "data": response["data"]})
    resp.set_cookie(
        key="COOKIE_AUTH",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=900
    )

    resp.set_cookie(
        key="COOKIE_REFRESH",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=604800,
    )

    return resp


@router.post("/forget-password", dependencies=FORGET_PASSWORD_RATE_LIMIT_DEPS)
async def forget_password(
        data: ForgetPasswordRequestModel,
        conn: asyncpg.Connection = Depends(postgresql.get_db),
        redis_client=Depends(redis_cache.get_redis),
        channel=Depends(rabbitmq.get_channel),
):
    response = await auth_service.forget_password(conn, redis_client, channel, data)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    token = response["data"].pop("access_token")
    resp = JSONResponse(
        status_code=200,
        content={"message": response["message"], "data": response["data"]},
    )
    resp.set_cookie(
        key=COOKIE_AUTH_RESET,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=RESET_COOKIE_MAX_AGE,
    )

    return resp


@router.post("/validate-code", dependencies=VALIDATE_CODE_RATE_LIMIT_DEPS)
async def validate_code(
        data: ValidateCodeRequest,
        user: dict = Depends(security.validate_token_to_validate_code),
        redis_client=Depends(redis_cache.get_redis),
):
    response = await auth_service.validate_reset_code(redis_client, user, data)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    token = response["data"].pop("access_token")
    resp = JSONResponse(
        status_code=200,
        content={"message": response["message"], "data": response["data"]},
    )
    resp.set_cookie(
        key=COOKIE_AUTH_RESET,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=RESET_COOKIE_MAX_AGE,
    )

    return resp


@router.post("/update-password")
async def update_password(
        data: UpdatePasswordRequest,
        user: dict = Depends(security.validate_token_to_update_password),
        conn: asyncpg.Connection = Depends(postgresql.get_db),
):
    response = await auth_service.update_password_after_reset(conn, user, data)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    resp = JSONResponse(
        status_code=200,
        content={"message": response["message"], "data": response["data"]},
    )
    resp.delete_cookie(key=COOKIE_AUTH_RESET, path="/", samesite="lax")

    return resp
