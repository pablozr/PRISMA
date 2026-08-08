import re
from enum import StrEnum

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator

FULL_NAME_MIN_LENGTH = 3
FULL_NAME_MAX_LENGTH = 150
GOOGLE_SUB_MIN_LENGTH = 6
GOOGLE_SUB_MAX_LENGTH = 255
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

GOOGLE_SUB_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,255}$")
SPECIAL_CHAR_PATTERN = re.compile(r"[!@#$%^&*()_\-+=\[\]{};:,.?/\\|~`\"']")


class UserRole(StrEnum):
    ADMIN = "admin"
    TECNICO = "tecnico"
    PROFESSOR = "professor"
    ALUNO = "aluno"


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=True,
        extra="forbid",
    )


def validate_full_name(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) < FULL_NAME_MIN_LENGTH:
        raise ValueError("O nome completo deve ter pelo menos 3 caracteres.")
    if len(normalized) > FULL_NAME_MAX_LENGTH:
        raise ValueError("O nome completo deve ter no maximo 150 caracteres.")
    if re.search(r"[\r\n\t]", normalized):
        raise ValueError("O nome completo contem caracteres invalidos.")
    return normalized


def validate_google_sub(value: str) -> str:
    normalized = value.strip()
    if len(normalized) < GOOGLE_SUB_MIN_LENGTH:
        raise ValueError("google_sub invalido.")
    if len(normalized) > GOOGLE_SUB_MAX_LENGTH:
        raise ValueError("google_sub deve ter no maximo 255 caracteres.")
    if not GOOGLE_SUB_PATTERN.fullmatch(normalized):
        raise ValueError("google_sub contem caracteres invalidos.")
    return normalized


def validate_strong_password(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError("A senha deve ter no maximo 128 caracteres.")
    if re.search(r"\s", value):
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


class UserBaseInput(BaseSchema):
    institutional_email: EmailStr
    full_name: str = Field(min_length=FULL_NAME_MIN_LENGTH, max_length=FULL_NAME_MAX_LENGTH)

    @field_validator("institutional_email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_full_name(value)


class CreateUserSchema(UserBaseInput):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH, repr=False)
    role: UserRole

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_strong_password(value)


class UserStatusUpdateRequest(BaseSchema):
    is_active: bool = Field(validation_alias=AliasChoices("is_active", "habilitado"))


class UserResponseData(BaseSchema):
    id: int
    institutional_email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool


class UserGetDataResponse(BaseSchema):
    user: UserResponseData


class UserGetResponse(BaseSchema):
    status: bool
    message: str
    data: UserGetDataResponse


class UserStatusUpdateDataResponse(BaseSchema):
    user_id: int = Field(validation_alias=AliasChoices("user_id", "usuario_id"))
    is_active: bool = Field(validation_alias=AliasChoices("is_active", "habilitado"))


class UserStatusUpdateResponse(BaseSchema):
    status: bool
    message: str
    data: UserStatusUpdateDataResponse


class CreateUserResponseData(UserResponseData):
    pass


class CreateUserResponse(BaseSchema):
    status: bool
    message: str
    data: CreateUserResponseData
