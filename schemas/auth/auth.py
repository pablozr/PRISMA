import re

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
REFRESH_TOKEN_MAX_LENGTH = 4096
RESET_CODE_LENGTH = 6

RESET_CODE_PATTERN = re.compile(r"^\d{6}$")
SPECIAL_CHAR_PATTERN = re.compile(r"[!@#$%^&*()_\-+=\[\]{};:,.?/\\|~`\"']")
WHITESPACE_PATTERN = re.compile(r"\s")


class BaseRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserLoginRequest(BaseRequestModel):
    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=PASSWORD_MAX_LENGTH,
        repr=False,
        validation_alias=AliasChoices("password", "senha"),
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A senha e obrigatoria.")
        return value


class ForgetPasswordRequestModel(BaseRequestModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class ValidateCodeRequest(BaseRequestModel):
    code: str = Field(
        min_length=RESET_CODE_LENGTH,
        max_length=RESET_CODE_LENGTH,
        validation_alias=AliasChoices("code", "codigo"),
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        normalized = value.strip()
        if not RESET_CODE_PATTERN.fullmatch(normalized):
            raise ValueError("O codigo deve conter exatamente 6 digitos numericos.")
        return normalized


class UpdatePasswordRequest(BaseRequestModel):
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        repr=False,
        validation_alias=AliasChoices("password", "nova_senha"),
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("A senha nao pode ter espacos no inicio ou fim.")
        if WHITESPACE_PATTERN.search(value):
            raise ValueError("A senha nao pode conter espacos em branco.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("A senha deve conter pelo menos uma letra maiuscula.")
        if not re.search(r"[a-z]", value):
            raise ValueError("A senha deve conter pelo menos uma letra minuscula.")
        if not re.search(r"\d", value):
            raise ValueError("A senha deve conter pelo menos um numero.")
        if not SPECIAL_CHAR_PATTERN.search(value):
            raise ValueError("A senha deve conter pelo menos um caractere especial.")
        return value


class RefreshTokenRequest(BaseRequestModel):
    refresh_token: str = Field(
        min_length=1,
        max_length=REFRESH_TOKEN_MAX_LENGTH,
        validation_alias=AliasChoices("refresh_token", "refreshToken"),
    )

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Token de atualizacao ausente.")
        return normalized
