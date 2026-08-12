from services.sie.normalizer import normalize_participation, normalize_project
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
    value = normalize_participation({"id_projeto": 1, "cpf": "1", "nome_participante": "Ana", "funcao_participante": "Bolsista", "tipo_vinculo_instituicao": None})
    assert value["profile"] == "aluno"
    assert value["permission_source"] is None


def test_missing_participant_identity_is_rejected():
    with pytest.raises(ValueError):
        normalize_participation({"id_projeto": 1, "funcao_participante": "Bolsista"})


def test_email_less_participation_uses_legacy_cpf_digest_for_continuity():
    participation = normalize_participation(
        {"id_projeto": 1, "cpf": "12345678900", "nome_participante": "Ana", "funcao_participante": "Bolsista"}
    )

    assert participation["source_identity_key"] == "a8476735b37a541a38402a2e7037c79e2d217fe9780e5e34347156ef61eff42b"
    assert participation["participation_fingerprint"] == "642289a2cc0c65b93aeecf82d978a6a8adf2e3332f8a40cce5c58f522aa42db5"
    assert participation["institutional_email"] is None


def test_same_name_and_function_without_stable_identity_are_rejected():
    row = {"id_projeto": 1, "nome_participante": "Ana", "funcao_participante": "Bolsista"}

    with pytest.raises(ValueError, match="cpf or institutional email"):
        normalize_participation(row)


def test_participation_normalizes_textual_weekly_hours():
    participation = normalize_participation(
        {"id_projeto": 1, "cpf": "1", "nome_participante": "Ana", "funcao_participante": "Bolsista", "carga_horaria_semanal": "20"}
    )
    assert participation["weekly_hours"] == 20


def test_participation_does_not_normalize_cpf_or_contact_fields():
    participation = normalize_participation(
        {
            "id_projeto": 1,
            "cpf": "12345678900",
            "nome_participante": "Ana",
            "funcao_participante": "Bolsista",
            "email_projeto_participante": "ana@unirio.br",
            "fone_celular_participante": "21999999999",
        }
    )

    assert participation["institutional_email"] == "ana@unirio.br"
    assert {"cpf", "project_email", "standard_email", "mobile_phone", "landline_phone"}.isdisjoint(participation)


def test_project_repairs_utf8_text_decoded_as_latin1():
    project = normalize_project(
        {
            "id_projeto": 1,
            "titulo": "EstratÃ©gia pedagÃ³gica",
            "resumo_projeto": "FormaÃ§Ã£o acadÃªmica",
        }
    )

    assert project["title"] == "Estratégia pedagógica"
    assert project["source_summary"] == "Formação acadêmica"
