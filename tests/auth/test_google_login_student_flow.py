import asyncio
import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from schemas.professor.professor import CreateProfessorSchema
from services.auth import auth_service


def test_create_professor_user_from_registry_returns_none_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()

    monkeypatch.setattr(auth_service, "get_active_professor_by_email", AsyncMock(return_value=None))
    create_professor_mock = AsyncMock()
    monkeypatch.setattr(auth_service, "create_user_professor_registry", create_professor_mock)

    result = asyncio.run(
        auth_service._create_professor_user_from_registry(
            conn,
            "prof@edu.unirio.br",
            "sub-prof",
        )
    )

    assert result is None
    create_professor_mock.assert_not_awaited()


def test_create_professor_user_from_registry_creates_user_when_found(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    professor_registry = {
        "full_name": "Prof Teste",
    }
    created_professor_user = {
        "id": 77,
        "institutional_email": "prof@edu.unirio.br",
        "full_name": "Prof Teste",
        "role": "professor",
    }

    monkeypatch.setattr(auth_service, "get_active_professor_by_email", AsyncMock(return_value=professor_registry))

    create_professor_mock = AsyncMock(return_value=created_professor_user)
    monkeypatch.setattr(auth_service, "create_user_professor_registry", create_professor_mock)

    result = asyncio.run(
        auth_service._create_professor_user_from_registry(
            conn,
            "prof@edu.unirio.br",
            "sub-prof",
        )
    )

    assert result == created_professor_user
    create_professor_mock.assert_awaited_once()
    _, professor_data = create_professor_mock.await_args.args
    assert isinstance(professor_data, CreateProfessorSchema)
    assert professor_data.institutional_email == "prof@edu.unirio.br"
    assert professor_data.full_name == "Prof Teste"
    assert professor_data.google_sub == "sub-prof"


def test_find_or_create_google_user_returns_none_when_email_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()

    get_user_mock = AsyncMock()
    monkeypatch.setattr(auth_service, "get_active_user_by_email", get_user_mock)

    result = asyncio.run(auth_service._find_or_create_google_user(conn, {"sub": "abc"}))

    assert result is None
    get_user_mock.assert_not_awaited()


def test_find_or_create_google_user_returns_existing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    existing_user = {
        "id": 5,
        "institutional_email": "user@edu.unirio.br",
        "role": "professor",
    }

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=existing_user))

    professor_mock = AsyncMock()
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", professor_mock)

    result = asyncio.run(
        auth_service._find_or_create_google_user(
            conn,
            {"email": "user@edu.unirio.br", "sub": "sub-existing", "name": "User Existing"},
        )
    )

    assert result == existing_user
    professor_mock.assert_not_awaited()


def test_find_or_create_google_user_returns_none_when_sub_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))

    professor_mock = AsyncMock()
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", professor_mock)

    result = asyncio.run(
        auth_service._find_or_create_google_user(
            conn,
            {"email": "sem.sub@edu.unirio.br", "name": "Sem Sub"},
        )
    )

    assert result is None
    professor_mock.assert_not_awaited()


def test_find_or_create_google_user_returns_professor_when_registry_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    professor_user = {
        "id": 11,
        "institutional_email": "prof@edu.unirio.br",
        "role": "professor",
    }

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))

    professor_mock = AsyncMock(return_value=professor_user)
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", professor_mock)

    result = asyncio.run(
        auth_service._find_or_create_google_user(
            conn,
            {
                "email": "prof@edu.unirio.br",
                "sub": "sub-prof",
                "name": "Professor Teste",
            },
        )
    )

    assert result == professor_user
    professor_mock.assert_awaited_once_with(conn, "prof@edu.unirio.br", "sub-prof")


def test_find_or_create_google_user_returns_none_if_professor_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    google_user = {
        "email": "aluno@edu.unirio.br",
        "sub": "google-sub",
        "name": "Aluno Teste",
    }

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", AsyncMock(return_value=None))

    result = asyncio.run(auth_service._find_or_create_google_user(conn, google_user))

    assert result is None


def test_find_or_create_google_user_ignores_name_when_professor_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    google_user = {
        "email": "sem.nome@edu.unirio.br",
        "sub": "sub-001",
    }

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", AsyncMock(return_value=None))

    result = asyncio.run(auth_service._find_or_create_google_user(conn, google_user))
    assert result is None


def test_find_or_create_google_user_returns_none_when_professor_cannot_be_created(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", AsyncMock(return_value=None))

    result = asyncio.run(
        auth_service._find_or_create_google_user(
            conn,
            {
                "email": "aluno@edu.unirio.br",
                "sub": "sub-xyz",
                "name": "Aluno X",
            },
        )
    )

    assert result is None
