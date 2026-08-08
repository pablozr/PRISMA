import hashlib
from datetime import date


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _normalized_email(row: dict) -> str | None:
    value = row.get("email_projeto_participante") or row.get("email_padrao_participante")
    return value.strip().lower() if value else None


def _profile(row: dict) -> str:
    if str(row.get("funcao_participante") or "").strip().lower() == "coordenador":
        return "professor"
    if str(row.get("tipo_vinculo_instituicao") or "").strip().lower() == "servidor":
        return "tecnico"
    return "aluno"


def normalize_project(row: dict) -> dict:
    title = str(row.get("titulo") or "").strip()
    if not title or row.get("id_projeto") is None:
        raise ValueError("SIE row requires id_projeto and titulo")
    return {
        "sie_project_id": int(row["id_projeto"]),
        "process_code": row.get("num_projeto"),
        "title": title,
        "source_summary": row.get("resumo_projeto"),
        "source_status": row.get("situacao_projeto"),
        "source_type": row.get("tipo_projeto"),
        "source_classification_id": row.get("id_classificacao"),
        "source_thematic_area": row.get("area_tematica_conhecimento"),
        "source_research_chamber": row.get("camara_pesquisa"),
        "has_external_funding": {"Sim": True, "Não": False}.get(row.get("fomento_externo")),
        "ethics_committee": row.get("comite_etica"),
        "sisgen_code": row.get("sisgen"),
        "registered_on": _optional_date(row.get("data_registro_projeto")),
        "starts_at": _optional_date(row.get("inicio_projeto")),
        "ends_at": _optional_date(row.get("termino_projeto")),
        "source_updated_on": _optional_date(row.get("data_ultima_alteracao")),
        "keywords": [row.get(f"palavra_chave0{position}") for position in range(1, 5)],
        "center_name": row.get("centro"),
        "executing_unit_name": row.get("unidade_responsavel"),
    }


def normalize_participation(row: dict) -> dict:
    full_name = str(row.get("nome_participante") or "").strip()
    participant_function = str(row.get("funcao_participante") or "").strip()
    if not full_name or not participant_function:
        raise ValueError("SIE row requires nome_participante and funcao_participante")
    email = _normalized_email(row)
    identity = row.get("cpf") or email or f"{full_name}:{row.get('id_projeto')}"
    fingerprint = hashlib.sha256(
        f"{identity}:{row.get('id_projeto')}:{participant_function}".encode()
    ).hexdigest()
    permission_source = None
    if _profile(row) == "professor":
        permission_source = "coordinator"
    elif _profile(row) == "tecnico":
        permission_source = "server_participant"
    return {
        "source_identity_key": hashlib.sha256(identity.encode()).hexdigest(),
        "full_name": full_name,
        "institutional_email": email,
        "cpf": row.get("cpf") or None,
        "profile": _profile(row),
        "participant_function": participant_function,
        "participation_fingerprint": fingerprint,
        "permission_source": permission_source,
        "scholarship_type": row.get("tipo_bolsa"),
        "participation_status": row.get("situacao_atual"),
        "degree": row.get("titulacao_participante"),
        "project_email": row.get("email_projeto_participante"),
        "standard_email": row.get("email_padrao_participante"),
        "mobile_phone": row.get("fone_celular_participante"),
        "landline_phone": row.get("fone_fixo_participante"),
        "weekly_hours": row.get("carga_horaria_semanal"),
        "institutional_link": row.get("tipo_vinculo_instituicao"),
        "admission_method": row.get("forma_ingresso"),
        "job_description": row.get("descr_cargo"),
        "work_schedule": row.get("jornada_trabalho"),
        "departure_method": row.get("forma_evasao"),
        "contract_status": row.get("situacao_contrato"),
        "possession_on": _optional_date(row.get("dt_posse")),
        "joined_on": _optional_date(row.get("dt_ingresso")),
        "left_on": _optional_date(row.get("dt_saida")),
        "participation_starts_on": _optional_date(row.get("inicio_participacao")),
        "participation_ends_on": _optional_date(row.get("termino_participacao")),
    }
