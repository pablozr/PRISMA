import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import HTTPException

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from core.security import rate_limit, security


def _build_request(
    path: str = "/auth/login",
    headers: dict | None = None,
    ip: str | None = "127.0.0.1",
    cookies: dict | None = None,
):
    return SimpleNamespace(
        headers=headers or {},
        client=SimpleNamespace(host=ip) if ip is not None else None,
        url=SimpleNamespace(path=path),
        cookies=cookies or {},
        state=SimpleNamespace(),
    )


def test_is_allowed_domain_accepts_allowed_email_and_hd() -> None:
    assert security.is_allowed_domain("aluno@edu.unirio.br", "edu.unirio.br") is True


def test_is_allowed_domain_rejects_when_hd_differs() -> None:
    assert security.is_allowed_domain("aluno@edu.unirio.br", "externo.com") is False


def test_is_allowed_domain_rejects_substring_domain_attack() -> None:
    assert security.is_allowed_domain("aluno@rio.br") is False


def test_client_ip_uses_forwarded_header() -> None:
    request = _build_request(headers={"X-Forwarded-For": "10.0.0.10, 10.0.0.20"}, ip="192.168.1.10")

    assert rate_limit._client_ip(request) == "10.0.0.10"


def test_client_ip_falls_back_to_client_host() -> None:
    request = _build_request(ip="172.16.0.15")

    assert rate_limit._client_ip(request) == "172.16.0.15"


def test_rate_limiter_sets_expire_on_first_request() -> None:
    redis_client = SimpleNamespace(
        incr=AsyncMock(return_value=1),
        expire=AsyncMock(),
    )
    request = _build_request(path="/auth/login", ip="10.10.10.10")

    dependency = rate_limit.rate_limiter(max_requests=3, window_seconds=60)
    result = asyncio.run(dependency(request, redis_client))

    assert result is True
    redis_client.incr.assert_awaited_once_with("rate_limit:/auth/login:10.10.10.10")
    redis_client.expire.assert_awaited_once_with("rate_limit:/auth/login:10.10.10.10", 60)


def test_rate_limiter_blocks_request_over_limit() -> None:
    redis_client = SimpleNamespace(
        incr=AsyncMock(return_value=4),
        expire=AsyncMock(),
    )
    request = _build_request(path="/auth/login", ip="10.10.10.11")

    dependency = rate_limit.rate_limiter(max_requests=3, window_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(request, redis_client))

    assert exc_info.value.status_code == 429
    redis_client.expire.assert_not_awaited()


def test_verify_token_returns_user_for_valid_auth_token_with_session(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "type": "auth",
        "userId": 42,
        "sessionId": "session-001",
    }
    expected_user = {"id": 42, "role": "professor"}

    monkeypatch.setattr(security, "decode_access_token", lambda _token: payload)
    monkeypatch.setattr(
        security.user_service,
        "get_one_user",
        AsyncMock(return_value={"status": True, "data": {"user": expected_user}}),
    )
    monkeypatch.setattr(
        security.cache_service,
        "get_by_key",
        AsyncMock(return_value={"userId": 42, "refreshJti": "jti"}),
    )

    result = asyncio.run(
        security.verify_token(
            "Bearer token",
            conn=object(),
            redis_client=object(),
            expected_type="auth",
        )
    )

    assert result == expected_user


def test_verify_token_returns_false_for_type_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security,
        "decode_access_token",
        lambda _token: {"type": "refresh", "userId": 1, "sessionId": "session-002"},
    )

    result = asyncio.run(
        security.verify_token(
            "token",
            conn=object(),
            redis_client=object(),
            expected_type="auth",
        )
    )

    assert result is False


def test_verify_token_returns_none_for_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_expired(_token: str) -> dict:
        raise jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr(security, "decode_access_token", raise_expired)

    result = asyncio.run(
        security.verify_token(
            "token",
            conn=object(),
            redis_client=object(),
            expected_type="auth",
        )
    )

    assert result is None


def test_verify_token_requires_valid_session_for_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security,
        "decode_access_token",
        lambda _token: {"type": "auth", "userId": 5, "sessionId": "session-missing"},
    )
    monkeypatch.setattr(
        security.user_service,
        "get_one_user",
        AsyncMock(return_value={"status": True, "data": {"user": {"id": 5, "role": "professor"}}}),
    )
    monkeypatch.setattr(security.cache_service, "get_by_key", AsyncMock(return_value=None))

    result = asyncio.run(
        security.verify_token(
            "token",
            conn=object(),
            redis_client=object(),
            expected_type="auth",
        )
    )

    assert result is False


def test_verify_token_allows_reset_with_can_update_true_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    expected_user = {"id": 9, "role": "professor"}

    monkeypatch.setattr(
        security,
        "decode_access_token",
        lambda _token: {"type": "reset", "userId": 9, "canUpdate": True},
    )
    monkeypatch.setattr(
        security.user_service,
        "get_one_user",
        AsyncMock(return_value={"status": True, "data": {"user": expected_user}}),
    )

    result = asyncio.run(
        security.verify_token(
            "token",
            conn=object(),
            redis_client=object(),
            expected_type="reset",
            check_can_update=True,
        )
    )

    assert result == expected_user


def test_validate_token_raises_when_cookie_missing() -> None:
    request = _build_request(cookies={})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            security.validate_token(
                request,
                conn=object(),
                redis_client=object(),
            )
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated"


def test_validate_token_raises_when_token_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _build_request(cookies={security.COOKIE_AUTH: "token"})

    monkeypatch.setattr(security, "verify_token", AsyncMock(return_value=None))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            security.validate_token(
                request,
                conn=object(),
                redis_client=object(),
            )
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"


def test_validate_token_returns_user_and_sets_request_state(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _build_request(cookies={security.COOKIE_AUTH: "token"})
    resolved_user = {"id": 12, "role": "professor"}

    monkeypatch.setattr(security, "verify_token", AsyncMock(return_value=resolved_user))

    result = asyncio.run(
        security.validate_token(
            request,
            conn=object(),
            redis_client=object(),
        )
    )

    assert result == resolved_user
    assert request.state.token == "token"


def test_require_professor_rank_blocks_unknown_role() -> None:
    dependency = security.require_professor_rank()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependency(user={"role": "visitor"}))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions"


def test_require_professor_rank_allows_professor() -> None:
    dependency = security.require_professor_rank()
    professor_user = {"role": "professor", "id": 55}

    result = asyncio.run(dependency(user=professor_user))

    assert result == professor_user


def test_require_manager_rank_allows_tecnico() -> None:
    dependency = security.require_manager_rank()
    tecnico_user = {"role": "tecnico", "id": 77}

    result = asyncio.run(dependency(user=tecnico_user))

    assert result == tecnico_user
