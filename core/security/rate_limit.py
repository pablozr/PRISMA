from fastapi import Depends, HTTPException, Request

from core.config.config import settings
from core.redis.redis_cache import redis_cache


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limiter(max_requests: int, window_seconds: int):
    async def dependency(request: Request, redis_client=Depends(redis_cache.get_redis)):
        ip = _client_ip(request)
        key = f"{settings.RATE_LIMIT_KEY_PREFIX}:{request.url.path}:{ip}"

        current_requests = await redis_client.incr(key)
        if current_requests == 1:
            await redis_client.expire(key, window_seconds)

        if current_requests > max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )

        return True

    return dependency


LOGIN_RATE_LIMIT_DEPS = [
    Depends(
        rate_limiter(
            settings.RATE_LIMIT_LOGIN_MAX_REQUESTS,
            settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
        )
    )
]
FORGET_PASSWORD_RATE_LIMIT_DEPS = [
    Depends(
        rate_limiter(
            settings.RATE_LIMIT_FORGET_PASSWORD_MAX_REQUESTS,
            settings.RATE_LIMIT_FORGET_PASSWORD_WINDOW_SECONDS,
        )
    )
]
VALIDATE_CODE_RATE_LIMIT_DEPS = [
    Depends(
        rate_limiter(
            settings.RATE_LIMIT_VALIDATE_CODE_MAX_REQUESTS,
            settings.RATE_LIMIT_VALIDATE_CODE_WINDOW_SECONDS,
        )
    )
]