import secrets
from datetime import timedelta
from pathlib import Path

import aio_pika
import asyncpg
import redis

from core.config.config import (
    EMAIL_FROM,
    EMAIL_QUEUE,
    RESET_CODE_REDIS_TTL_SECONDS,
    RESET_COOKIE_MAX_AGE,
    settings,
)
from core.logger.logger import logger
from core.security.hashing import verify_password, hash_password
from core.security.security import create_token, decode_access_token
from functions.utils.utils import build_login_success_response, extract_user_identity, service_response
from repositories.people.people_repository import create_user_from_person, get_person_by_email
from repositories.user.user_repository import get_active_user_by_email
from repositories.user.user_repository import (
    get_active_user_for_password_reset,
    get_active_user_with_password_by_email,
    update_user_password,
)
from schemas.auth.auth import (
    ForgetPasswordRequestModel,
    UpdatePasswordRequest,
    UserLoginRequest,
    ValidateCodeRequest,
)
from integrations.google_oauth_client import google_oauth_client
from services.cache import cache_service
from services.queue import queue_service

SESSION_TTL_SECONDS = 60 * 60 * 24 * 7


async def _create_session_tokens(user: dict, redis_client: redis.Redis) -> tuple[str, str]:
    user_id, email, role = extract_user_identity(user)
    session_id = secrets.token_hex(16)
    refresh_jti = secrets.token_hex(16)

    access_token = create_token(
        {
            "userId": user_id,
            "email": email,
            "role": role,
            "sessionId": session_id,
            "type": "auth",
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_token(
        {
            "userId": user_id,
            "email": email,
            "role": role,
            "sessionId": session_id,
            "jti": refresh_jti,
            "type": "refresh",
        },
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )

    await cache_service.set_by_key(
        key=f"session:{session_id}",
        ttl_seconds=SESSION_TTL_SECONDS,
        value={"userId": user_id, "refreshJti": refresh_jti},
        redis_client=redis_client,
    )

    return access_token, refresh_token

async def _create_user_from_imported_person(
        conn: asyncpg.Connection,
        email: str,
        google_sub: str,
) -> dict | None:
    """
    Tenta criar um usuário do tipo professor com base em um registro existente na tabela professor_registry.
     - Se existir um registro ativo na tabela professor_registry com o email fornecido e sem um user_id associado, cria um usuário do tipo
     professor usando as informações do registro e associa o user_id do novo usuário ao registro.
     - Se não existir um registro correspondente ou se o registro já tiver um user_id associado, retorna
     None, indicando que não foi possível criar um usuário do tipo professor com base no registro.
    """
    person = await get_person_by_email(conn, email)
    if not person or person.get("user_id") is not None:
        return None
    return await create_user_from_person(conn, email, google_sub)


async def _find_or_create_google_user(conn: asyncpg.Connection, google_user: dict) -> dict | None:
    email = google_user.get("email")
    if not email:
        return None

    user = await get_active_user_by_email(conn, email)
    if user:
        return user

    google_sub = google_user.get("sub")
    if not google_sub:
        return None

    # Tenta achar um professor registrado com o email do Google e criar o usuário com base nesse registro
    return await _create_user_from_imported_person(conn, email, google_sub)


async def login(conn: asyncpg.Connection, redis_client: redis.Redis, login_data: UserLoginRequest) -> dict:
    try:
        user_record = await get_active_user_with_password_by_email(conn, login_data.email)
        if not user_record:
            return service_response(status=False, message="Email ou senha incorretos")

        if user_record["role"] != "admin":
            return service_response(status=False, message="Erro interno")

        password_hash = user_record["password_hash"]
        if not password_hash or not verify_password(login_data.password, password_hash):
            return service_response(status=False, message="Email ou senha incorretos")

        access_token, refresh_token = await _create_session_tokens(dict(user_record), redis_client)
        return build_login_success_response(access_token, refresh_token)
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def logout(redis_client: redis.Redis, session_id: str | None) -> dict:
    try:
        await cache_service.delete_by_key(f"session:{session_id}", redis_client)
        return service_response(status=True, message="Logout realizado com sucesso")
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def refresh_token(redis_client: redis.Redis, refresh_token: str) -> dict:
    try:
        if not refresh_token:
            return service_response(status=False, message="Token de atualizacao ausente")

        if refresh_token.startswith("Bearer "):
            refresh_token = refresh_token[7:]

        payload = decode_access_token(refresh_token)

        if payload.get("type") != "refresh":
            raise ValueError("Tipo de token invalido")

        if not payload.get("userId") or not payload.get("sessionId"):
            raise ValueError("Token invalido")

        session = await cache_service.get_by_key(
            f"session:{payload['sessionId']}", redis_client
        )
        if not session or session.get("refreshJti") != payload.get("jti"):
            raise ValueError("Sessao invalida")

        await cache_service.delete_by_key(f"session:{payload['sessionId']}", redis_client)

        token_user = {
            "id": payload.get("userId"),
            "email": payload.get("email"),
            "role": payload.get("role"),
        }
        new_access_token, new_refresh_token = await _create_session_tokens(token_user, redis_client)

        return service_response(status=True, message="Tokens atualizados com sucesso",
                                data={"accessToken": new_access_token, "refreshToken": new_refresh_token})
    except ValueError as e:
        logger.error(str(e))
        return service_response(status=False, message="Token invalido")
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def google_oauth_start(redis_client: redis.Redis) -> dict:
    try:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)

        await cache_service.set_by_key(
            key=f"google_oauth_state:{state}",
            ttl_seconds=settings.GOOGLE_OAUTH_STATE_TTL_SECONDS,
            value={"nonce": nonce},
            redis_client=redis_client,
        )

        return service_response(
            status=True,
            message="URL de autenticacao Google gerada com sucesso",
            data={"authorizationUrl": google_oauth_client.build_authorization_url(state, nonce)},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def google_oauth_callback(
        conn: asyncpg.Connection,
        redis_client: redis.Redis,
        code: str,
        state: str,
) -> dict:
    try:
        cache_key = f"google_oauth_state:{state}"
        oauth_state = await cache_service.get_by_key(cache_key, redis_client)
        if not oauth_state or not oauth_state.get("nonce"):
            return service_response(status=False, message="Estado OAuth invalido")

        await cache_service.delete_by_key(cache_key, redis_client)
        token_response = await google_oauth_client.exchange_code(code)
        raw_id_token = token_response.get("id_token")
        if not raw_id_token:
            return service_response(status=False, message="Google token invalido")

        google_user = google_oauth_client.verify_id_token(raw_id_token, oauth_state["nonce"])
        user = await _find_or_create_google_user(conn, google_user)
        if not user:
            return service_response(status=False, message="Usuario nao autorizado")

        access_token, refresh_token = await _create_session_tokens(user, redis_client)
        login_response = build_login_success_response(access_token, refresh_token)
        if not login_response["status"]:
            return login_response

        try:
            session_id = decode_access_token(login_response["data"]["accessToken"]).get("sessionId")
        except Exception:
            session_id = None

        if session_id:
            login_response["data"]["sessionId"] = session_id

        return login_response
    except ValueError as e:
        logger.error(str(e))
        return service_response(status=False, message=str(e))
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def forget_password(
        conn: asyncpg.Connection,
        redis_client,
        channel: aio_pika.abc.AbstractChannel,
        data: ForgetPasswordRequestModel,
) -> dict:
    try:
        row = await get_active_user_for_password_reset(conn, data.email)

        if not row:
            return service_response(status=False, message="Usuario nao encontrado")

        code = f"{secrets.randbelow(1_000_000):06d}"
        cache_key = f"{row['id']}:{row['institutional_email']}"

        await cache_service.set_by_key(
            key=cache_key,
            ttl_seconds=RESET_CODE_REDIS_TTL_SECONDS,
            value={"code": code},
            redis_client=redis_client,
        )

        template_path = Path(__file__).resolve().parents[2] / "templates" / "reset_password_email.html"
        html = template_path.read_text(encoding="utf-8").replace("CODE_HERE", code)

        await queue_service.publish(
            EMAIL_QUEUE,
            {
                "to": data.email,
                "from": EMAIL_FROM,
                "subject": "Codigo para redefinicao de senha",
                "html": html,
                "message": "",
                "base64Attachment": "",
                "base64AttachmentName": "",
            },
            channel,
        )

        reset_payload = {
            "userId": row["id"],
            "email": row["institutional_email"],
            "fullname": row["full_name"],
            "role": row["role"],
            "canUpdate": False,
            "type": "reset",
        }
        token = create_token(
            reset_payload, expires_delta=timedelta(seconds=RESET_COOKIE_MAX_AGE)
        )

        return service_response(
            status=True,
            message="Codigo de verificacao enviado",
            data={"access_token": token},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def validate_reset_code(
        redis_client, user: dict, data: ValidateCodeRequest
) -> dict:
    try:
        user_id = user.get("userId") or user.get("id")
        email = user.get("email") or user.get("institutional_email")
        role = user.get("role")

        if user_id is None or not email or not role:
            return service_response(status=False, message="Token invalido")

        full_name = user.get("fullname") or user.get("full_name") or email.split("@")[0]
        cache_key = f"{user_id}:{email}"
        redis_data = await cache_service.get_by_key(cache_key, redis_client)

        if not redis_data or redis_data.get("code") != data.code:
            return service_response(status=False, message="Codigo invalido ou expirado")

        await cache_service.delete_by_key(cache_key, redis_client)

        reset_payload = {
            "userId": int(user_id),
            "email": str(email),
            "fullname": str(full_name),
            "role": str(role),
            "canUpdate": True,
            "type": "reset",
        }
        token = create_token(
            reset_payload, expires_delta=timedelta(seconds=RESET_COOKIE_MAX_AGE)
        )

        return service_response(
            status=True,
            message="Codigo validado com sucesso",
            data={"access_token": token},
        )
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def update_password_after_reset(
        conn: asyncpg.Connection, user: dict, data: UpdatePasswordRequest
) -> dict:
    try:
        user_id = user.get("userId") or user.get("id")
        if user_id is None:
            return service_response(status=False, message="Token invalido")

        hashed = hash_password(data.password)

        row = await update_user_password(conn, int(user_id), hashed)

        if not row:
            return service_response(status=False, message="Usuario nao encontrado")

        return service_response(
            status=True,
            message="Senha atualizada com sucesso",
            data={
                "user": {
                    "id": row["id"],
                    "institutional_email": row["institutional_email"],
                    "full_name": row["full_name"],
                    "role": row["role"],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            },
        )
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")
