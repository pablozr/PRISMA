import secrets
from datetime import timedelta

import asyncpg
import aio_pika
import redis

from core.config.config import settings
from core.logger.logger import logger
from core.security.hashing import verify_password
from core.security.security import create_token, is_allowed_domain, verify_google_token, decode_access_token
from functions.utils.utils import service_response
from repositories.professor.professor_repository import (
    create_user_professor_registry,
    get_active_professor_by_email,
)
from repositories.user.user_repository import create_student_user, get_active_user_by_email
from schemas.auth.auth import (
    ForgetPasswordRequestModel,
    UpdatePasswordRequest,
    UserLoginGoogleRequest,
    UserLoginRequest,
    ValidateCodeRequest,
)
from schemas.professor.professor import CreateProfessorSchema
from schemas.user.user import CreateStudentUserSchema
from services.cache import cache_service

SESSION_TTL_SECONDS = 60 * 60 * 24 * 7


def _extract_user_identity(user: dict) -> tuple[int, str, str]:
    user_id = user.get("id")
    email = user.get("email") or user.get("institutional_email")
    role = user.get("role")

    if user_id is None or not email or not role:
        raise ValueError("Invalid user identity")

    return user_id, email, role


async def _create_session_tokens(user: dict, redis_client: redis.Redis) -> tuple[str, str]:
    user_id, email, role = _extract_user_identity(user)
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


async def _login_success_response(user: dict, redis_client: redis.Redis) -> dict:
    access_token, refresh_token = await _create_session_tokens(user, redis_client)
    return service_response(
        status=True,
        message="Login successful",
        data={"accessToken": access_token, "refreshToken": refresh_token},
    )


async def _create_professor_user_from_registry(
        conn: asyncpg.Connection,
        email: str,
        google_sub: str,
) -> dict | None:
    professor = await get_active_professor_by_email(conn, email)
    if not professor:
        return None

    professor_data = CreateProfessorSchema(
        institutional_email=email,
        full_name=professor["full_name"],
        google_sub=google_sub,
    )

    return await create_user_professor_registry(conn, professor_data)


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

    professor_user = await _create_professor_user_from_registry(conn, email, google_sub)
    if professor_user:
        return professor_user

    full_name = google_user.get("name") or email.split("@")[0]
    student_data = CreateStudentUserSchema(
        institutional_email=email,
        full_name=full_name,
        google_sub=google_sub,
    )

    return await create_student_user(conn, student_data)


async def login(conn: asyncpg.Connection, redis_client: redis.Redis, login_data: UserLoginRequest) -> dict:
    query = """
            SELECT id,
                   institutional_email,
                   password_hash,
                   role
            FROM users
            WHERE institutional_email = $1
              AND is_active = TRUE LIMIT 1;
            """

    try:
        user_record = await conn.fetchrow(query, login_data.email)
        if not user_record:
            return service_response(status=False, message="Email ou senha incorretos")

        if user_record["role"] != "admin":
            return service_response(status=False, message="Erro interno")

        password_hash = user_record["password_hash"]
        if not password_hash or not verify_password(login_data.password, password_hash):
            return service_response(status=False, message="Email ou senha incorretos")

        return await _login_success_response(dict(user_record), redis_client)
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def logout(redis_client: redis.Redis, session_id: str | None) -> dict:
    try:
        await cache_service.delete_by_key(f"session:{session_id}", redis_client)
        return service_response(status=True, message="Logout successful")
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def refresh_token(redis_client: redis.Redis, refresh_token: str) -> dict:
    try:
        if not refresh_token:
            return service_response(status=False, message="Refresh token ausente")

        if refresh_token.startswith("Bearer "):
            refresh_token = refresh_token[7:]

        payload = decode_access_token(refresh_token)

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        if not payload.get("userId") or not payload.get("sessionId"):
            raise ValueError("Invalid token")

        session = await cache_service.get_by_key(
            f"session:{payload['sessionId']}", redis_client
        )
        if not session or session.get("refreshJti") != payload.get("jti"):
            raise ValueError("Invalid session")

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
        return service_response(status=False, message="Token inválido")
    except Exception as e:
        logger.exception(e)
        return service_response(status=False, message="Erro interno")


async def google_login(
        conn: asyncpg.Connection,
        redis_client: redis.Redis,
        google_data: UserLoginGoogleRequest,
) -> dict:
    """Realiza o login usando um token do Google. O processo inclui:
    1. Verificar a validade do token do Google e extrair as informações do usuário.
    2. Validar o domínio do email do usuário contra o dominio permitido.
    3. Procurar um usuário existente com o email extraído. Se não existir,
        criar um novo usuário, verificando primeiro se o email corresponde a um professor registrado,
        caso pertença a um professor registrado, criar o usuário com base nas informações do registro do professor,
        caso contrário, criar um usuário do tipo estudante.
    """
    try:
        google_user = verify_google_token(google_data.credential)
        if not google_user:
            return service_response(status=False, message="Google token invalido")

        email = google_user.get("email")
        if not email:
            return service_response(status=False, message="Google token invalido")

        if not is_allowed_domain(email, google_user.get("hd")):
            return service_response(status=False, message="Dominio de email nao permitido")

        user = await _find_or_create_google_user(conn, google_user)
        if not user:
            return service_response(status=False, message="Usuario nao autorizado")

        return await _login_success_response(user, redis_client)
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
        row = await conn.fetchrow(
            "SELECT id, fullname, email, role FROM users WHERE email = $1", data.email
        )

        if not row:
            return {"status": False, "message": "User not found", "data": {}}

        code = generate_temp_code()
        cache_key = f"{row['id']}:{row['email']}"

        await cache_service.set_by_key(
            cache_key, RESET_CODE_REDIS_TTL, {"code": code}, redis_client
        )

        html = RESET_PASSWORD_EMAIL_TEMPLATE.replace("CODE_HERE", code)

        await messaging_service.publish(
            EMAIL_QUEUE,
            {
                "to": data.email,
                "from": settings.EMAIL_FROM,
                "subject": "Password reset code",
                "html": html,
                "message": "",
                "base64Attachment": "",
                "base64AttachmentName": "",
            },
            channel,
        )

        reset_payload = reset_jwt_payload(
            row["id"],
            row["email"],
            row["fullname"],
            row["role"],
            can_update=False,
        )
        token = create_token(
            reset_payload, expires_delta=timedelta(seconds=RESET_COOKIE_MAX_AGE)
        )

        return {
            "status": True,
            "message": "Verification code sent",
            "data": {"access_token": token},
        }
    except Exception as e:
        logger.exception(e)
        return {"status": False, "message": "Internal server error", "data": {}}


async def validate_reset_code(
        redis_client, user: dict, data: ValidateCodeRequest
) -> dict:
    try:
        cache_key = f"{user['userId']}:{user['email']}"
        redis_data = await cache_service.get_by_key(cache_key, redis_client)

        if not redis_data or redis_data.get("code") != data.code:
            return {"status": False, "message": "Invalid or expired code", "data": {}}

        await cache_service.delete_by_key(cache_key, redis_client)

        reset_payload = reset_jwt_payload(
            user["userId"],
            user["email"],
            user["fullname"],
            user["role"],
            can_update=True,
        )
        token = create_token(
            reset_payload, expires_delta=timedelta(seconds=RESET_COOKIE_MAX_AGE)
        )

        return {
            "status": True,
            "message": "Code validated",
            "data": {"access_token": token},
        }
    except Exception as e:
        logger.exception(e)
        return {"status": False, "message": "Internal server error", "data": {}}


async def update_password_after_reset(
        conn: asyncpg.Connection, user: dict, data: UpdatePasswordRequest
) -> dict:
    try:
        hashed = hash_password(data.password)

        row = await conn.fetchrow(
            """
            UPDATE users
            SET password   = $1,
                updated_at = NOW()
            WHERE id = $2 RETURNING id, fullname, email, role, created_at
            """,
            hashed,
            user["userId"],
        )

        if not row:
            return {"status": False, "message": "User not found", "data": {}}

        return {
            "status": True,
            "message": "Password updated successfully",
            "data": {"user": user_from_row(row)},
        }
    except Exception as e:
        logger.exception(e)
        return {"status": False, "message": "Internal server error", "data": {}}
