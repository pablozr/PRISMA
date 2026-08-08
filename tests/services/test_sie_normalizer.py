from services.sie.normalizer import normalize_participation
import pytest


def test_coordinator_becomes_professor_with_edit_permission():
    row = {"id_projeto": 1, "cpf": "1", "nome_participante": "Ana", "funcao_participante": "Coordenador"}
    value = normalize_participation(row)
    assert value["profile"] == "professor"
    assert value["permission_source"] == "coordinator"


def test_server_becomes_technician_with_edit_permission():
    row = {"id_projeto": 1, "cpf": "1", "nome_participante": "Ana", "funcao_participante": "Bolsista", "tipo_vinculo_instituicao": "Servidor"}
    value = normalize_participation(row)
    assert value["profile"] == "tecnico"
    assert value["permission_source"] == "server_participant"


def test_student_cannot_edit_and_nullable_source_values_are_supported():
    value = normalize_participation({"id_projeto": 1, "nome_participante": "Ana", "funcao_participante": "Bolsista", "tipo_vinculo_instituicao": None})
    assert value["profile"] == "aluno"
    assert value["permission_source"] is None


def test_missing_participant_identity_is_rejected():
    with pytest.raises(ValueError):
        normalize_participation({"id_projeto": 1, "funcao_participante": "Bolsista"})
