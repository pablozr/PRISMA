import pytest
from pydantic import ValidationError

from schemas.auth.auth import UpdatePasswordRequest, UserLoginRequest, ValidateCodeRequest
from schemas.user.user import UserStatusUpdateRequest, validate_google_sub


def test_login_request_accepts_senha_alias_and_normalizes_email() -> None:
    payload = UserLoginRequest.model_validate(
        {
            "email": "ALUNO@EDU.UNIRIO.BR",
            "senha": "Secret1!",
        }
    )

    assert payload.email == "aluno@edu.unirio.br"
    assert payload.password == "Secret1!"


def test_login_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        UserLoginRequest.model_validate(
            {
                "email": "aluno@edu.unirio.br",
                "password": "Secret1!",
                "unexpected": "field",
            }
        )


def test_validate_code_accepts_legacy_codigo_alias() -> None:
    payload = ValidateCodeRequest.model_validate({"codigo": "123456"})

    assert payload.code == "123456"


def test_update_password_requires_special_character() -> None:
    with pytest.raises(ValidationError):
        UpdatePasswordRequest.model_validate({"password": "Senha1234"})


def test_user_status_update_accepts_habilitado_alias() -> None:
    payload = UserStatusUpdateRequest.model_validate({"habilitado": True})

    assert payload.is_active is True


def test_validate_google_sub_rejects_invalid_characters() -> None:
    with pytest.raises(ValueError):
        validate_google_sub("sub invalido")
