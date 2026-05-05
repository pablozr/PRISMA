import asyncio
import os
from unittest.mock import AsyncMock, Mock

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from schemas.auth.auth import UserLoginRequest
from services.auth import auth_service


def test_login_common_allows_only_admin_with_valid_credentials(monkeypatch) -> None:
    conn = AsyncMock()
    redis_client = object()
    admin_row = {
        "id": 1,
        "institutional_email": "admin@edu.unirio.br",
        "password_hash": "hashed-password",
        "role": "admin",
    }
    conn.fetchrow = AsyncMock(return_value=admin_row)

    verify_password_mock = Mock(return_value=True)
    create_tokens_mock = AsyncMock(return_value=("token-a", "token-r"))

    monkeypatch.setattr(auth_service, "verify_password", verify_password_mock)
    monkeypatch.setattr(auth_service, "_create_session_tokens", create_tokens_mock)

    result = asyncio.run(
        auth_service.login(
            conn,
            redis_client,
            UserLoginRequest(email="admin@edu.unirio.br", password="Admin123!"),
        )
    )

    assert result["status"] is True
    verify_password_mock.assert_called_once_with("Admin123!", "hashed-password")
    create_tokens_mock.assert_awaited_once_with(dict(admin_row), redis_client)


def test_login_common_rejects_student_even_with_valid_password(monkeypatch) -> None:
    conn = AsyncMock()
    redis_client = object()
    student_row = {
        "id": 2,
        "institutional_email": "aluno@edu.unirio.br",
        "password_hash": "hashed-password",
        "role": "student",
    }
    conn.fetchrow = AsyncMock(return_value=student_row)

    verify_password_mock = Mock(return_value=True)
    create_tokens_mock = AsyncMock()

    monkeypatch.setattr(auth_service, "verify_password", verify_password_mock)
    monkeypatch.setattr(auth_service, "_create_session_tokens", create_tokens_mock)

    result = asyncio.run(
        auth_service.login(
            conn,
            redis_client,
            UserLoginRequest(email="aluno@edu.unirio.br", password="Aluno123!"),
        )
    )

    assert result["status"] is False
    verify_password_mock.assert_not_called()
    create_tokens_mock.assert_not_awaited()


def test_login_common_rejects_professor_even_with_valid_password(monkeypatch) -> None:
    conn = AsyncMock()
    redis_client = object()
    professor_row = {
        "id": 3,
        "institutional_email": "prof@edu.unirio.br",
        "password_hash": "hashed-password",
        "role": "professor",
    }
    conn.fetchrow = AsyncMock(return_value=professor_row)

    verify_password_mock = Mock(return_value=True)
    create_tokens_mock = AsyncMock()

    monkeypatch.setattr(auth_service, "verify_password", verify_password_mock)
    monkeypatch.setattr(auth_service, "_create_session_tokens", create_tokens_mock)

    result = asyncio.run(
        auth_service.login(
            conn,
            redis_client,
            UserLoginRequest(email="prof@edu.unirio.br", password="Prof123!"),
        )
    )

    assert result["status"] is False
    verify_password_mock.assert_not_called()
    create_tokens_mock.assert_not_awaited()
