from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MAX_LENGTH = 128
REFRESH_TOKEN_MAX_LENGTH = 4096


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
