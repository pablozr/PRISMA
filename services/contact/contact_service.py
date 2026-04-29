from html import escape

import asyncpg
from aio_pika.abc import AbstractChannel

from core.config.config import EMAIL_FROM, EMAIL_QUEUE
from core.logger.logger import logger
from functions.utils.utils import service_response, extract_authenticated_user_context
from repositories.contact.contact_repository import (
    create_contact_email_request,
    get_contact_email_request_status,
)
from schemas.notification.email_dispatch_request import ContactEmailCreateRequest
from services.queue import queue_service


def _build_contact_email_html(body: str) -> str:
    escaped_body = escape(body).replace("\n", "<br>")
    return f"<p>{escaped_body}</p>"


async def create_contact_email(
    conn: asyncpg.Connection,
    user: dict,
    channel: AbstractChannel,
    data: ContactEmailCreateRequest,
) -> dict:
    try:
        user_context = extract_authenticated_user_context(user)
        if user_context is None:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role = user_context
        if user_role != "student":
            return service_response(False, "Apenas alunos podem solicitar contato por email.")

        base_payload = {
            "requestedByUserId": user_id,
            "projectId": data.project_id,
            "type": "project_contact_email",
        }

        async with conn.transaction():
            request = await create_contact_email_request(
                conn=conn,
                requested_by_user_id=user_id,
                project_id=data.project_id,
                subject=data.subject,
                body=data.body,
                payload=base_payload,
            )

            if not request:
                return service_response(False, "Projeto nao encontrado ou indisponivel para contato.")

            await queue_service.publish(
                EMAIL_QUEUE,
                {
                    "requestId": request["request_id"],
                    "to": request["to_email"],
                    "from": EMAIL_FROM,
                    "subject": request["subject"],
                    "html": _build_contact_email_html(request["body"]),
                    "message": request["body"],
                    "base64Attachment": "",
                    "base64AttachmentName": "",
                },
                channel,
            )

        return service_response(
            True,
            "Solicitacao de contato criada com sucesso.",
            data={"request": {"request_id": request["request_id"], "status": request["status"]}},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao criar solicitacao de contato.")


async def get_contact_email_status(
    conn: asyncpg.Connection,
    user: dict,
    request_id: int,
) -> dict:
    try:
        user_context = extract_authenticated_user_context(user)
        if user_context is None:
            return service_response(False, "Usuario autenticado invalido.")

        user_id, user_role = user_context
        if user_role not in {"student", "admin"}:
            return service_response(False, "Usuario sem permissao para consultar esta solicitacao.")

        request = await get_contact_email_request_status(
            conn=conn,
            request_id=request_id,
            user_id=user_id,
            user_role=user_role,
        )

        if not request:
            return service_response(False, "Solicitacao de contato nao encontrada.")

        return service_response(
            True,
            "Solicitacao de contato recuperada com sucesso.",
            data={"request": request},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(False, "Erro ao consultar solicitacao de contato.")
