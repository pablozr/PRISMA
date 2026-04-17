from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    ENVIRONMENT: str = "development"
    API_PORT: int = 8000

    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    GOOGLE_CLIENT_ID: str

    COOKIE_AUTH: str = "auth"
    COOKIE_AUTH_REFRESH: str = "refresh"
    COOKIE_AUTH_RESET: str = "reset"

    ROLE_RANK_BY_NAME: dict[str, int] = Field(
        default_factory=lambda: {
            "STUDENT": 1,
            "PROFESSOR": 2,
            "ADMIN": 3,
        }
    )

    RATE_LIMIT_KEY_PREFIX: str = "rate_limit"
    RATE_LIMIT_LOGIN_MAX_REQUESTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60
    RATE_LIMIT_FORGET_PASSWORD_MAX_REQUESTS: int = 3
    RATE_LIMIT_FORGET_PASSWORD_WINDOW_SECONDS: int = 300
    RATE_LIMIT_VALIDATE_CODE_MAX_REQUESTS: int = 5
    RATE_LIMIT_VALIDATE_CODE_WINDOW_SECONDS: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

# Backward-compatible aliases for modules still importing constants directly.
COOKIE_AUTH = settings.COOKIE_AUTH
COOKIE_AUTH_REFRESH = settings.COOKIE_AUTH_REFRESH
COOKIE_AUTH_RESET = settings.COOKIE_AUTH_RESET
ROLE_RANK_BY_NAME = settings.ROLE_RANK_BY_NAME

RATE_LIMIT_KEY_PREFIX = settings.RATE_LIMIT_KEY_PREFIX
RATE_LIMIT_LOGIN_MAX_REQUESTS = settings.RATE_LIMIT_LOGIN_MAX_REQUESTS
RATE_LIMIT_LOGIN_WINDOW_SECONDS = settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS
RATE_LIMIT_FORGET_PASSWORD_MAX_REQUESTS = settings.RATE_LIMIT_FORGET_PASSWORD_MAX_REQUESTS
RATE_LIMIT_FORGET_PASSWORD_WINDOW_SECONDS = settings.RATE_LIMIT_FORGET_PASSWORD_WINDOW_SECONDS
RATE_LIMIT_VALIDATE_CODE_MAX_REQUESTS = settings.RATE_LIMIT_VALIDATE_CODE_MAX_REQUESTS
RATE_LIMIT_VALIDATE_CODE_WINDOW_SECONDS = settings.RATE_LIMIT_VALIDATE_CODE_WINDOW_SECONDS
