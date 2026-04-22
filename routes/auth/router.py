import asyncpg
import redis
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from core.security.rate_limit import LOGIN_RATE_LIMIT_DEPS
from schemas.auth.auth import UserLoginRequest
from services.auth.auth_service import login as auth_login, logout as auth_logout, refresh_token as auth_refresh

router = APIRouter()


@router.post("/login", dependencies=LOGIN_RATE_LIMIT_DEPS)
async def login(conn: asyncpg.Connection, redis_client: redis.Redis, data: UserLoginRequest):
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


@router.post("/logout")
async def logout(request: Request, redis_client: redis.Redis):
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


@router.post("/refresh", dependencies=LOGIN_RATE_LIMIT_DEPS)
async def refresh_token(request: Request, redis_client: redis.Redis):
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
