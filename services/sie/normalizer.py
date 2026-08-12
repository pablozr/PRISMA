import hashlib
from datetime import date


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not any(marker in text for marker in ("Ã", "Â", "â")):
        return text or None

    marker_count = sum(text.count(marker) for marker in ("Ã", "Â", "â"))
    for encoding in ("latin-1", "cp1252"):
        try:
            candidate = text.encode(encoding).decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError):
            continue

        candidate_marker_count = sum(candidate.count(marker) for marker in ("Ã", "Â", "â"))
        if candidate_marker_count < marker_count:
            return candidate

    return text or None


def _normalized_email(row: dict) -> str | None:
    value = _normalize_text(row.get("email_projeto_participante") or row.get("email_padrao_participante"))
    return value.lower() if value else None


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _profile(row: dict) -> str:
    if str(row.get("funcao_participante") or "").strip().lower() == "coordenador":
        return "professor"
    if str(row.get("tipo_vinculo_instituicao") or "").strip().lower() == "servidor":
        return "tecnico"
    return "aluno"


def normalize_project(row: dict) -> dict:
    title = _normalize_text(row.get("titulo")) or ""
    if not title or row.get("id_projeto") is None:
        raise ValueError("SIE row requires id_projeto and titulo")
    return {
        "sie_project_id": int(row["id_projeto"]),
        "process_code": _normalize_text(row.get("num_projeto")),
        "title": title,
        "source_summary": _normalize_text(row.get("resumo_projeto")),
        "source_status": _normalize_text(row.get("situacao_projeto")),
        "source_type": _normalize_text(row.get("tipo_projeto")),
        "source_classification_id": row.get("id_classificacao"),
        "source_thematic_area": _normalize_text(row.get("area_tematica_conhecimento")),
        "source_research_chamber": _normalize_text(row.get("camara_pesquisa")),
        "has_external_funding": {"Sim": True, "Não": False}.get(row.get("fomento_externo")),
        "ethics_committee": _normalize_text(row.get("comite_etica")),
        "sisgen_code": _normalize_text(row.get("sisgen")),
        "registered_on": _optional_date(row.get("data_registro_projeto")),
        "starts_at": _optional_date(row.get("inicio_projeto")),
        "ends_at": _optional_date(row.get("termino_projeto")),
        "source_updated_on": _optional_date(row.get("data_ultima_alteracao")),
        "keywords": [_normalize_text(row.get(f"palavra_chave0{position}")) for position in range(1, 5)],
        "center_name": _normalize_text(row.get("centro")),
        "executing_unit_name": _normalize_text(row.get("unidade_responsavel")),
    }


def normalize_participation(row: dict) -> dict:
    full_name = str(row.get("nome_participante") or "").strip()
    participant_function = str(row.get("funcao_participante") or "").strip()
    if not full_name or not participant_function:
        raise ValueError("SIE row requires nome_participante and funcao_participante")
    email = _normalized_email(row)
    # Preserve the pre-PII-migration identity order. CPF is used only while
    # normalizing this source row; only its digest is persisted.
    identity = row.get("cpf") or email
    if not identity:
        raise ValueError("SIE participant requires cpf or institutional email")
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
        "profile": _profile(row),
        "participant_function": participant_function,
        "participation_fingerprint": fingerprint,
        "permission_source": permission_source,
        "scholarship_type": row.get("tipo_bolsa"),
        "participation_status": row.get("situacao_atual"),
        "degree": row.get("titulacao_participante"),
        "weekly_hours": _optional_int(row.get("carga_horaria_semanal")),
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
