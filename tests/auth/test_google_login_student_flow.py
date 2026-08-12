import asyncio
from unittest.mock import AsyncMock

from integrations.google_oauth_client import GoogleOAuthClient
from integrations import google_oauth_client
from routes.auth import router as auth_router
from services.auth import auth_service


def test_imported_person_creates_google_user(monkeypatch) -> None:
    conn = object()
    person = {"id": 10, "full_name": "Aluno", "profile": "aluno", "user_id": None}
    created_user = {"id": 20, "institutional_email": "aluno@edu.unirio.br", "role": "aluno"}
    monkeypatch.setattr(auth_service, "get_person_by_email", AsyncMock(return_value=person))
    create_user = AsyncMock(return_value=created_user)
    monkeypatch.setattr(auth_service, "create_user_from_person", create_user)

    result = asyncio.run(
        auth_service._create_user_from_imported_person(conn, "aluno@edu.unirio.br", "google-sub")
    )

    assert result == created_user
    create_user.assert_awaited_once_with(conn, "aluno@edu.unirio.br", "google-sub")


def test_google_login_requires_imported_person(monkeypatch) -> None:
    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service, "get_person_by_email", AsyncMock(return_value=None))

    result = asyncio.run(
        auth_service._find_or_create_google_user(
            object(), {"email": "novo@edu.unirio.br", "sub": "google-sub"}
        )
    )

    assert result is None


def test_existing_google_user_is_linked_to_imported_person(monkeypatch) -> None:
    conn = object()
    user = {"id": 20, "institutional_email": "aluno@edu.unirio.br", "role": "aluno"}
    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=user))
    link_person = AsyncMock()
    monkeypatch.setattr(auth_service, "link_existing_user_to_person", link_person)

    result = asyncio.run(
        auth_service._find_or_create_google_user(
            conn, {"email": "aluno@edu.unirio.br", "sub": "google-sub"}
        )
    )

    assert result == user
    link_person.assert_awaited_once_with(conn, 20, "aluno@edu.unirio.br")


def test_google_token_verification_allows_small_clock_skew(monkeypatch) -> None:
    calls = {}

    def fake_verify(raw_token, request, audience, clock_skew_in_seconds=0):
        calls["clock_skew_in_seconds"] = clock_skew_in_seconds
        return {"iss": "accounts.google.com", "nonce": "nonce", "email_verified": True, "email": "aluno@edu.unirio.br", "hd": "edu.unirio.br"}

    monkeypatch.setattr(google_oauth_client.id_token, "verify_oauth2_token", fake_verify)

    GoogleOAuthClient().verify_id_token("token", "nonce")

    assert calls["clock_skew_in_seconds"] > 0


def test_google_callback_redirects_with_error_code(monkeypatch) -> None:
    monkeypatch.setattr(
        auth_router,
        "auth_google_oauth_callback",
        AsyncMock(return_value={"status": False, "message": "Google token invalido", "data": {}}),
    )

    response = asyncio.run(auth_router.google_oauth_callback(code="code", state="state", conn=object(), redis_client=object()))

    assert response.headers["location"].endswith("/signin?error=google_auth_failed")
