from starlette.responses import JSONResponse, RedirectResponse

from core.config.config import COOKIE_AUTH, COOKIE_AUTH_REFRESH


def set_auth_cookies(resp: JSONResponse | RedirectResponse, access_token: str, refresh_token: str, session_id: str | None = None) -> None:
    resp.set_cookie(
        key=COOKIE_AUTH,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=900,
    )

    resp.set_cookie(
        key=COOKIE_AUTH_REFRESH,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=604800,
    )

    if session_id:
        resp.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
            max_age=604800,
        )
