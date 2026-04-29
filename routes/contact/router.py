from fastapi import APIRouter, Depends

from core.postgresql.postgresql import postgresql
from core.rabbitmq.rabbitmq import rabbitmq
from core.security import security
from functions.utils.utils import default_response
from schemas.notification.email_dispatch_request import ContactEmailCreateRequest
from services.contact.contact_service import create_contact_email, get_contact_email_status

router = APIRouter()


@router.post("/email")
async def post_contact_email(
    data: ContactEmailCreateRequest,
    user=Depends(security.validate_token_wrapper),
    conn=Depends(postgresql.get_db),
    channel=Depends(rabbitmq.get_channel),
):
    return await default_response(create_contact_email, [conn, user, channel, data], is_creation=True)


@router.get("/email/{request_id}")
async def get_contact_email(
    request_id: int,
    user=Depends(security.require_admin_rank),
    conn=Depends(postgresql.get_db),
):
    return await default_response(get_contact_email_status, [conn, user, request_id])


@router.get("/email/me")
async def get_contact_email_sent_by_me(
    user=Depends(security.validate_token_wrapper),
    conn=Depends(postgresql.get_db),
):
    return await default_response(get_contact_email_sent_by_me, [conn, user])
