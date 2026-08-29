from repositories.project.project_repository import _decode_json_columns, _project_contract_columns


def test_decode_json_columns_returns_api_objects() -> None:
    row = {
        "institutional": '{"summary":"Resumo"}',
        "editorial": '{"areas":[]}',
        "contacts": '[{"full_name":"Ana","institutional_email":"ana@unirio.br","role":"professor"}]',
        "opportunities": "[]",
    }

    result = _decode_json_columns(
        row,
        {
            "institutional": {},
            "editorial": {},
            "contacts": [],
            "opportunities": [],
        },
    )

    assert result["institutional"] == {"summary": "Resumo"}
    assert result["editorial"] == {"areas": []}
    assert result["contacts"] == [{"full_name": "Ana", "institutional_email": "ana@unirio.br", "role": "professor"}]
    assert result["opportunities"] == []


def test_project_contract_includes_project_contacts() -> None:
    query = _project_contract_columns()

    assert "FROM project_participations participation" in query
    assert "person.institutional_email" in query
    assert "LOWER(participation.participant_function)='coordenador'" in query
    assert "AS contacts" in query
