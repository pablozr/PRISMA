from typing import TypedDict

from .auth import (
    ForgetPasswordRequestModel,
    RefreshTokenRequest,
    UpdatePasswordRequest,
    UserLoginRequest,
    ValidateCodeRequest,
)

PasswordSendCodeRequest = ForgetPasswordRequestModel
PasswordValidateCodeRequest = ValidateCodeRequest
AuthLoginRequest = UserLoginRequest
AuthRefreshRequest = RefreshTokenRequest


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
