import secrets
from datetime import timedelta

import asyncpg
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
from schemas.auth.auth import UserLoginGoogleRequest, UserLoginRequest
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
