from pydantic import BaseModel


class CreateProfessorSchema(BaseModel):
    institutional_email: str
    full_name: str
    google_sub: str