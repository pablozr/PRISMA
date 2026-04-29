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

from schemas.notification.email_dispatch_request import ContactEmailCreateRequest
from services.contact import contact_service


class _DummyTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummyConn:
    def transaction(self):
        return _DummyTransaction()


def test_create_contact_email_persists_and_publishes_queue_event(monkeypatch: pytest.MonkeyPatch) -> None:
    create_mock = AsyncMock(
        return_value={
            "request_id": 12,
            "project_id": 5,
            "to_email": "prof@edu.unirio.br",
            "subject": "Interesse no projeto",
            "body": "Tenho interesse.",
            "status": "queued",
        }
    )
    publish_mock = AsyncMock()
    monkeypatch.setattr(contact_service, "create_contact_email_request", create_mock)
    monkeypatch.setattr(contact_service.queue_service, "publish", publish_mock)

    data = ContactEmailCreateRequest(
        project_id=5,
        subject="  Interesse no projeto  ",
        body="  Tenho interesse.  ",
    )
    channel = object()

    result = asyncio.run(
        contact_service.create_contact_email(
            conn=_DummyConn(),
            user={"id": 7, "role": "student"},
            channel=channel,
            data=data,
        )
    )

    assert result["status"] is True
    assert result["data"] == {"request": {"request_id": 12, "status": "queued"}}
    create_mock.assert_awaited_once()
    create_args = create_mock.await_args.kwargs
    assert create_args["requested_by_user_id"] == 7
    assert create_args["project_id"] == 5
    assert create_args["subject"] == "Interesse no projeto"
    assert create_args["body"] == "Tenho interesse."
    publish_mock.assert_awaited_once()
    queue_name, payload, used_channel = publish_mock.await_args.args
    assert queue_name == contact_service.EMAIL_QUEUE
    assert payload["requestId"] == 12
    assert payload["to"] == "prof@edu.unirio.br"
    assert payload["message"] == "Tenho interesse."
    assert used_channel is channel


def test_create_contact_email_rejects_non_student(monkeypatch: pytest.MonkeyPatch) -> None:
    create_mock = AsyncMock()
    publish_mock = AsyncMock()
    monkeypatch.setattr(contact_service, "create_contact_email_request", create_mock)
    monkeypatch.setattr(contact_service.queue_service, "publish", publish_mock)

    result = asyncio.run(
        contact_service.create_contact_email(
            conn=_DummyConn(),
            user={"id": 2, "role": "professor"},
            channel=object(),
            data=ContactEmailCreateRequest(project_id=5, subject="Assunto", body="Mensagem"),
        )
    )

    assert result["status"] is False
    assert "Apenas alunos" in result["message"]
    create_mock.assert_not_awaited()
    publish_mock.assert_not_awaited()


def test_get_contact_email_status_allows_admin_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    status_mock = AsyncMock(return_value={"request_id": 99, "status": "sent", "attempt_count": 1})
    monkeypatch.setattr(contact_service, "get_contact_email_request_status", status_mock)
    conn = object()

    result = asyncio.run(
        contact_service.get_contact_email_status(
            conn=conn,
            user={"id": 1, "role": "admin"},
            request_id=99,
        )
    )

    assert result["status"] is True
    assert result["data"] == {"request": {"request_id": 99, "status": "sent", "attempt_count": 1}}
    status_mock.assert_awaited_once_with(conn=conn, request_id=99, user_id=1, user_role="admin")
