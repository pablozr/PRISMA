from pydantic import BaseModel


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserLoginGoogleRequest(BaseModel):
    credential: str
