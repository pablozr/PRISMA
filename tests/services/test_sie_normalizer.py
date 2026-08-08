from services.sie.normalizer import normalize_participation


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
