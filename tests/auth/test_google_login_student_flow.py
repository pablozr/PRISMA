import asyncio
import os
from unittest.mock import AsyncMock, Mock

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from repositories.user.user_repository import create_student_user
from schemas.auth.auth import UserLoginGoogleRequest
from schemas.professor.professor import CreateProfessorSchema
from schemas.user.user import CreateStudentUserSchema
from services.auth import auth_service


def test_create_student_user_runs_insert_query() -> None:
    conn = AsyncMock()
    db_row = {
        "id": 10,
        "institutional_email": "aluno@edu.unirio.br",
        "full_name": "Aluno Teste",
        "role": "student",
        "google_sub": "google-sub",
        "is_active": True,
        "created_at": "2026-04-17T10:00:00",
        "updated_at": "2026-04-17T10:00:00",
    }
    conn.fetchrow = AsyncMock(return_value=db_row)

    data = CreateStudentUserSchema(
        institutional_email="aluno@edu.unirio.br",
        full_name="Aluno Teste",
        google_sub="google-sub",
    )

    result = asyncio.run(create_student_user(conn, data))

    assert result == db_row
    conn.fetchrow.assert_awaited_once()
    query, email, full_name, google_sub = conn.fetchrow.await_args.args
    assert "INSERT INTO users" in query
    assert "'student'" in query
    assert email == data.institutional_email
    assert full_name == data.full_name
    assert google_sub == data.google_sub


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
        "role": "student",
    }

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=existing_user))

    professor_mock = AsyncMock()
    student_mock = AsyncMock()
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", professor_mock)
    monkeypatch.setattr(auth_service, "create_student_user", student_mock)

    result = asyncio.run(
        auth_service._find_or_create_google_user(
            conn,
            {"email": "user@edu.unirio.br", "sub": "sub-existing", "name": "User Existing"},
        )
    )

    assert result == existing_user
    professor_mock.assert_not_awaited()
    student_mock.assert_not_awaited()


def test_find_or_create_google_user_returns_none_when_sub_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))

    professor_mock = AsyncMock()
    student_mock = AsyncMock()
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", professor_mock)
    monkeypatch.setattr(auth_service, "create_student_user", student_mock)

    result = asyncio.run(
        auth_service._find_or_create_google_user(
            conn,
            {"email": "sem.sub@edu.unirio.br", "name": "Sem Sub"},
        )
    )

    assert result is None
    professor_mock.assert_not_awaited()
    student_mock.assert_not_awaited()


def test_find_or_create_google_user_returns_professor_when_registry_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    professor_user = {
        "id": 11,
        "institutional_email": "prof@edu.unirio.br",
        "role": "professor",
    }

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))

    professor_mock = AsyncMock(return_value=professor_user)
    student_mock = AsyncMock()
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", professor_mock)
    monkeypatch.setattr(auth_service, "create_student_user", student_mock)

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
    student_mock.assert_not_awaited()


def test_find_or_create_google_user_creates_student_if_professor_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    google_user = {
        "email": "aluno@edu.unirio.br",
        "sub": "google-sub",
        "name": "Aluno Teste",
    }
    created_user = {
        "id": 7,
        "institutional_email": "aluno@edu.unirio.br",
        "full_name": "Aluno Teste",
        "role": "student",
        "google_sub": "google-sub",
        "is_active": True,
    }

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", AsyncMock(return_value=None))

    create_student_mock = AsyncMock(return_value=created_user)
    monkeypatch.setattr(auth_service, "create_student_user", create_student_mock)

    result = asyncio.run(auth_service._find_or_create_google_user(conn, google_user))

    assert result == created_user
    create_student_mock.assert_awaited_once()
    _, student_data = create_student_mock.await_args.args
    assert isinstance(student_data, CreateStudentUserSchema)
    assert student_data.institutional_email == "aluno@edu.unirio.br"
    assert student_data.full_name == "Aluno Teste"
    assert student_data.google_sub == "google-sub"


def test_find_or_create_google_user_uses_email_prefix_when_name_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    google_user = {
        "email": "sem.nome@edu.unirio.br",
        "sub": "sub-001",
    }

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", AsyncMock(return_value=None))

    create_student_mock = AsyncMock(return_value={"id": 8, "role": "student"})
    monkeypatch.setattr(auth_service, "create_student_user", create_student_mock)

    asyncio.run(auth_service._find_or_create_google_user(conn, google_user))

    create_student_mock.assert_awaited_once()
    _, student_data = create_student_mock.await_args.args
    assert student_data.full_name == "sem.nome"


def test_find_or_create_google_user_returns_none_when_student_creation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()

    monkeypatch.setattr(auth_service, "get_active_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service, "_create_professor_user_from_registry", AsyncMock(return_value=None))
    monkeypatch.setattr(auth_service, "create_student_user", AsyncMock(return_value=None))

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


def test_google_login_returns_invalid_when_google_token_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "verify_google_token", lambda _: None)

    result = asyncio.run(
        auth_service.google_login(
            object(),
            object(),
            UserLoginGoogleRequest(credential="invalid-credential"),
        )
    )

    assert result["status"] is False
    assert result["message"] == "Google token invalido"


def test_google_login_returns_invalid_when_google_email_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "verify_google_token", lambda _: {"sub": "sub-missing-email"})

    result = asyncio.run(
        auth_service.google_login(
            object(),
            object(),
            UserLoginGoogleRequest(credential="credential-without-email"),
        )
    )

    assert result["status"] is False
    assert result["message"] == "Google token invalido"


def test_google_login_blocks_disallowed_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    redis_client = object()

    google_payload = {
        "email": "aluno@dominio-externo.com",
        "sub": "sub-003",
        "hd": "dominio-externo.com",
    }

    find_user_mock = AsyncMock()

    monkeypatch.setattr(auth_service, "verify_google_token", lambda _: google_payload)
    monkeypatch.setattr(auth_service, "is_allowed_domain", lambda _email, _hd=None: False)
    monkeypatch.setattr(auth_service, "_find_or_create_google_user", find_user_mock)

    result = asyncio.run(
        auth_service.google_login(
            conn,
            redis_client,
            UserLoginGoogleRequest(credential="valid-credential"),
        )
    )

    assert result["status"] is False
    assert result["message"] == "Dominio de email nao permitido"
    find_user_mock.assert_not_awaited()


def test_google_login_returns_unauthorized_when_user_cannot_be_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    redis_client = object()

    google_payload = {
        "email": "desconhecido@edu.unirio.br",
        "sub": "sub-004",
        "hd": "edu.unirio.br",
    }

    find_user_mock = AsyncMock(return_value=None)
    login_success_mock = AsyncMock()

    monkeypatch.setattr(auth_service, "verify_google_token", lambda _: google_payload)
    monkeypatch.setattr(auth_service, "is_allowed_domain", lambda _email, _hd=None: True)
    monkeypatch.setattr(auth_service, "_find_or_create_google_user", find_user_mock)
    monkeypatch.setattr(auth_service, "_login_success_response", login_success_mock)

    result = asyncio.run(
        auth_service.google_login(
            conn,
            redis_client,
            UserLoginGoogleRequest(credential="valid-credential"),
        )
    )

    assert result["status"] is False
    assert result["message"] == "Usuario nao autorizado"
    login_success_mock.assert_not_awaited()


def test_google_login_returns_success_for_student_creation_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    redis_client = object()

    google_payload = {
        "email": "aluno@edu.unirio.br",
        "sub": "sub-002",
        "name": "Aluno Novo",
        "hd": "edu.unirio.br",
    }
    resolved_user = {
        "id": 9,
        "institutional_email": "aluno@edu.unirio.br",
        "role": "student",
    }
    login_response = {
        "status": True,
        "message": "Login successful",
        "data": {"accessToken": "token-a", "refreshToken": "token-r"},
    }

    monkeypatch.setattr(auth_service, "verify_google_token", lambda _: google_payload)
    monkeypatch.setattr(auth_service, "is_allowed_domain", lambda _email, _hd=None: True)

    find_user_mock = AsyncMock(return_value=resolved_user)
    login_success_mock = AsyncMock(return_value=login_response)

    monkeypatch.setattr(auth_service, "_find_or_create_google_user", find_user_mock)
    monkeypatch.setattr(auth_service, "_login_success_response", login_success_mock)

    result = asyncio.run(
        auth_service.google_login(
            conn,
            redis_client,
            UserLoginGoogleRequest(credential="valid-credential"),
        )
    )

    assert result == login_response
    find_user_mock.assert_awaited_once_with(conn, google_payload)
    login_success_mock.assert_awaited_once_with(resolved_user, redis_client)


def test_google_login_returns_internal_error_when_exception_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_runtime_error(_credential: str) -> dict:
        raise RuntimeError("google provider unavailable")

    logger_exception_mock = Mock()

    monkeypatch.setattr(auth_service, "verify_google_token", raise_runtime_error)
    monkeypatch.setattr(auth_service.logger, "exception", logger_exception_mock)

    result = asyncio.run(
        auth_service.google_login(
            object(),
            object(),
            UserLoginGoogleRequest(credential="credential"),
        )
    )

    assert result["status"] is False
    assert result["message"] == "Erro interno"
    logger_exception_mock.assert_called_once()