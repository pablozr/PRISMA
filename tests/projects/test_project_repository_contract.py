from repositories.project.project_repository import _decode_json_columns


def test_decode_json_columns_returns_api_objects() -> None:
    row = {
        "institutional": '{"summary":"Resumo"}',
        "editorial": '{"areas":[]}',
        "opportunities": "[]",
    }

    result = _decode_json_columns(
        row,
        {
            "institutional": {},
            "editorial": {},
            "opportunities": [],
        },
    )

    assert result["institutional"] == {"summary": "Resumo"}
    assert result["editorial"] == {"areas": []}
    assert result["opportunities"] == []
