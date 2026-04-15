from typing import TypedDict

from pydantic import BaseModel


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
