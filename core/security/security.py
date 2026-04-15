import jwt
from datetime import datetime, timedelta, timezone
from core.logger.logger import logger
from core.config.config import settings
from core.postgresql.postgresql import postgresql
from services.user import user_service
from fastapi import Request, HTTPException, Depends
from google.oauth2 import id_token
from google.auth.transport import requests


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.error("Invalid token")
        return None


def verify_google_token(token: str) -> dict | None:
    try:
        user = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)

        return {**user}
    except ValueError as e:
        logger.error(e)
        return None


async def verify_token(token: str, conn) -> dict | bool | None:
    try:

        if token.startswith("Bearer "):
            token = token[7:]

        payload = decode_access_token(token)

        if payload["userId"]:
            response = await user_service.get_one_user(conn, payload["userId"])

            if response["status"] is None or not response["status"]:
                raise jwt.InvalidSignatureError("User not found")

            return dict(response["data"]["user"])
        else:
            raise jwt.InvalidTokenError("Invalid token payload")

    # I use None to represent expired, and False to invalid *
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.error(f"Invalid token")
        return False


async def validate_token(request: Request, conn) -> dict:
    try:
        cookie_key = "auth"
        token = request.cookies.get(cookie_key)

        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user = await verify_token(token, conn=conn)

        # I use None to represent expired, and False to invalid **
        if user is None:
            raise HTTPException(status_code=401, detail="Token has expired")
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        request.state.token = token

        return user

    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=401, detail="Invalid token")


async def validate_token_wrapper(request: Request, conn=Depends(postgresql.get_db)) -> dict:
    return await validate_token(request, conn)


# ==========================================================
# JUST IN CASE IN THE FUTURE I NEED TO CONTROL ROLE ACCESS
# ==========================================================

def require_minimum_rank(minimum_rank: int, user: dict):

    role_ranks = {
        "BASIC": 1,
        "ADMIN": 2
    }

    user_role = user.get("role", "").upper()
    rank = role_ranks.get(user_role, 0)

    if rank < minimum_rank:
        raise HTTPException(status_code=403, detail="User doesn't have enough rank")

    return user


async def require_admin_rank(user = Depends(validate_token_wrapper)):
    return require_minimum_rank(2, user)
