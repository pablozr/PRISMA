import asyncpg
import redis
from fastapi import APIRouter, Request, Depends
from starlette.responses import JSONResponse, RedirectResponse

from core.config.config import COOKIE_AUTH, COOKIE_AUTH_REFRESH, COOKIE_AUTH_RESET, RESET_COOKIE_MAX_AGE, settings
from core.cookies.cookies import set_auth_cookies
from core.postgresql.postgresql import postgresql
from core.rabbitmq.rabbitmq import rabbitmq
from core.redis.redis_cache import redis_cache
from core.security import security
from core.security.rate_limit import LOGIN_RATE_LIMIT_DEPS, VALIDATE_CODE_RATE_LIMIT_DEPS, \
    FORGET_PASSWORD_RATE_LIMIT_DEPS
from core.security.security import decode_access_token, validate_token_refresh, validate_token_wrapper
from schemas.auth.auth import (
    ForgetPasswordRequestModel,
    UpdatePasswordRequest,
    UserLoginRequest,
    ValidateCodeRequest,
)
from services.auth import auth_service
from services.auth.auth_service import (
    google_oauth_callback as auth_google_oauth_callback,
    google_oauth_start as auth_google_oauth_start,
    login as auth_login,
    logout as auth_logout,
    refresh_token as auth_refresh,
)

router = APIRouter()


@router.post("/login", dependencies=LOGIN_RATE_LIMIT_DEPS)
async def login(
        data: UserLoginRequest,
        conn: asyncpg.Connection = Depends(postgresql.get_db),
        redis_client: redis.Redis = Depends(redis_cache.get_redis),
):
    response = await auth_login(conn, redis_client, data)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    access_token = response["data"].pop("accessToken")
    refresh_token = response["data"].pop("refreshToken")

    resp = JSONResponse(status_code=200, content={"message": response["message"], "data": response["data"]})
    set_auth_cookies(resp, access_token, refresh_token)

    return resp


@router.get("/google/start", dependencies=LOGIN_RATE_LIMIT_DEPS)
async def google_oauth_start(redis_client: redis.Redis = Depends(redis_cache.get_redis)):
    response = await auth_google_oauth_start(redis_client)
    if not response["status"]:
        return RedirectResponse(settings.FRONTEND_AUTH_ERROR_URL, status_code=302)

    return RedirectResponse(response["data"]["authorizationUrl"], status_code=302)


@router.get("/google/callback", dependencies=LOGIN_RATE_LIMIT_DEPS)
async def google_oauth_callback(
        code: str | None = None,
        state: str | None = None,
        conn: asyncpg.Connection = Depends(postgresql.get_db),
        redis_client: redis.Redis = Depends(redis_cache.get_redis),
):
    if not code or not state:
        return RedirectResponse(settings.FRONTEND_AUTH_ERROR_URL, status_code=302)

    response = await auth_google_oauth_callback(conn, redis_client, code, state)
    if not response["status"]:
        return RedirectResponse(settings.FRONTEND_AUTH_ERROR_URL, status_code=302)

    access_token = response["data"].get("accessToken")
    refresh_token = response["data"].get("refreshToken")
    session_id = response["data"].get("sessionId")

    if not access_token or not refresh_token:
        return RedirectResponse(settings.FRONTEND_AUTH_ERROR_URL, status_code=302)

    redirect_response = RedirectResponse(settings.FRONTEND_AUTH_SUCCESS_URL, status_code=302)
    set_auth_cookies(redirect_response, access_token, refresh_token, session_id)
    return redirect_response


@router.get("/me")
async def me(user: dict = Depends(validate_token_wrapper)):
    return JSONResponse(
        status_code=200,
        content={"message": "Authenticated user retrieved", "data": {"user": user}},
    )


@router.post("/logout")
async def logout(
        request: Request,
        _user: dict = Depends(validate_token_wrapper),
        redis_client: redis.Redis = Depends(redis_cache.get_redis),
):
    session_id = request.cookies.get("session_id")

    if not session_id and getattr(request.state, "token", None):
        try:
            session_id = decode_access_token(request.state.token).get("sessionId")
        except Exception:
            session_id = None

    if not session_id:
        return JSONResponse(status_code=400, content={"detail": "Session ID cookie is missing"})

    response = await auth_logout(redis_client, session_id)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    resp = JSONResponse(status_code=200, content={"message": response["message"], "data": response["data"]})
    resp.delete_cookie(COOKIE_AUTH, path="/", samesite="lax")
    resp.delete_cookie(COOKIE_AUTH_REFRESH, path="/", samesite="lax")
    resp.delete_cookie("session_id", path="/", samesite="lax")

    return resp


@router.post("/refresh", dependencies=[*LOGIN_RATE_LIMIT_DEPS, Depends(validate_token_refresh)])
async def refresh_token(request: Request, redis_client: redis.Redis = Depends(redis_cache.get_redis)):
    response = await auth_refresh(redis_client, request.state.token)

    if not response["status"]:
        return JSONResponse(status_code=400, content={"detail": response["message"]})

    access_token = response["data"].pop("accessToken")
    refresh_token = response["data"].pop("refreshToken")

    session_id = response["data"].pop("sessionId", None)
    if not session_id:
        try:
            session_id = decode_access_token(access_token).get("sessionId")
        except Exception:
            session_id = None

    resp = JSONResponse(status_code=200, content={"message": response["message"], "data": response["data"]})
    set_auth_cookies(resp, access_token, refresh_token, session_id)

    return resp


@router.post("/forget-password", dependencies=FORGET_PASSWORD_RATE_LIMIT_DEPS)
async def forget_password(
        data: ForgetPasswordRequestModel,
        conn: asyncpg.Connection = Depends(postgresql.get_db),
        redis_client: redis.Redis = Depends(redis_cache.get_redis),
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
        redis_client: redis.Redis = Depends(redis_cache.get_redis),
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
