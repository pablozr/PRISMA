from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel


class UserData(TypedDict):
    id: int
    institutional_email: str
    full_name: str
    password_hash: Optional[str]
    google_sub: Optional[str]
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class UserGetDataResponse(TypedDict):
    user_id: int
    email: str


class UserGetResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, UserGetDataResponse]


class UserStatusUpdateRequest(BaseModel):
    habilitado: bool


class UserStatusUpdateDataResponse(TypedDict):
    usuario_id: int
    habilitado: bool


class UserStatusUpdateResponse(TypedDict):
    status: bool
    message: str
    data: dict[str, UserStatusUpdateDataResponse]
