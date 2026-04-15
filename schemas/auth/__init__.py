from typing import TypedDict

from pydantic import BaseModel


class PasswordSendCodeRequest(BaseModel):
    email: str


class PasswordSendCodeData(TypedDict):
    email: str


class PasswordSendCodeResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, PasswordSendCodeData]


class PasswordValidateCodeRequest(BaseModel):
    email: str
    codigo: str
    nova_senha: str


class PasswordValidateCodeData(TypedDict):
    email: str


class PasswordValidateCodeResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, PasswordValidateCodeData]


class AuthLoginRequest(BaseModel):
    email: str
    senha: str


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class AuthGoogleLoginRequest(BaseModel):
    google_id_token: str


class AuthSessionData(TypedDict):
    user_id: int
    institutional_email: str
    full_name: str
    access_token: str
    refresh_token: str
    token_type: str


class AuthLoginResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AuthSessionData]


class AuthRefreshResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AuthSessionData]


class AuthGoogleLoginResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AuthSessionData]


class AuthLogoutData(TypedDict):
    revoked: bool


class AuthLogoutResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AuthLogoutData]


class AuthMeData(TypedDict):
    user_id: int
    institutional_email: str
    full_name: str
    is_active: bool
    roles: list[str]


class AuthMeResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, AuthMeData]
