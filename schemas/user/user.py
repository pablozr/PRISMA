from typing import TypedDict

from pydantic import BaseModel


class UserGetDataResponse(TypedDict):
    id: int
    institutional_email: str
    full_name: str
    role: str
    is_active: bool


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


class CreateStudentUserSchema(BaseModel):
    institutional_email: str
    full_name: str
    google_sub: str
