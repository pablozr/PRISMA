import asyncio
import json
import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
os.environ.setdefault("DB_NAME", "siepa")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client")

from routes.contact import router as contact_router_module
from schemas.notification.email_dispatch_request import ContactEmailCreateRequest


def test_post_contact_email_forwards_payload_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 7, "role": "student"}
    channel = object()
    service_mock = AsyncMock(
        return_value={
            "status": True,
            "message": "Solicitacao criada.",
            "data": {"request": {"request_id": 10, "status": "queued"}},
        }
    )
    monkeypatch.setattr(contact_router_module, "create_contact_email", service_mock)

    data = ContactEmailCreateRequest(project_id=5, subject="Assunto", body="Mensagem")
    response = asyncio.run(
        contact_router_module.post_contact_email(data=data, user=user, conn=conn, channel=channel)
    )

    assert response.status_code == 201
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["data"] == {"request": {"request_id": 10, "status": "queued"}}
    service_mock.assert_awaited_once_with(conn, user, channel, data)


def test_get_contact_email_forwards_request_id_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 7, "role": "student"}
    service_mock = AsyncMock(
        return_value={
            "status": True,
            "message": "ok",
            "data": {"request": {"request_id": 10, "status": "sent"}},
        }
    )
    monkeypatch.setattr(contact_router_module, "get_contact_email_status", service_mock)

    response = asyncio.run(contact_router_module.get_contact_email(request_id=10, user=user, conn=conn))

    assert response.status_code == 200
    service_mock.assert_awaited_once_with(conn, user, 10)


def test_get_contact_email_returns_400_when_service_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        contact_router_module,
        "get_contact_email_status",
        AsyncMock(return_value={"status": False, "message": "Solicitacao nao encontrada.", "data": {}}),
    )

    response = asyncio.run(contact_router_module.get_contact_email(request_id=404, user={"id": 7, "role": "student"}, conn=object()))

    assert response.status_code == 400
    assert json.loads(response.body.decode("utf-8")) == {"detail": "Solicitacao nao encontrada."}


def test_get_contact_email_sent_by_me_forwards_user_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = object()
    user = {"id": 7, "role": "student"}
    service_mock = AsyncMock(
        return_value={
            "status": True,
            "message": "ok",
            "data": {
                "requests": [
                    {
                        "request_id": 10,
                        "project_id": 5,
                        "to_email": "prof@edu.unirio.br",
                        "subject": "Interesse",
                        "body": "Mensagem",
                        "status": "sent",
                    }
                ]
            },
        }
    )
    monkeypatch.setattr(contact_router_module, "get_contact_emails_sent_by_me", service_mock)

    response = asyncio.run(contact_router_module.get_contact_email_sent_by_me(user=user, conn=conn))

    assert response.status_code == 200
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["data"]["requests"][0]["request_id"] == 10
    service_mock.assert_awaited_once_with(conn, user)
