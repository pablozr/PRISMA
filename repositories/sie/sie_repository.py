import asyncpg


async def create_sync_run(conn: asyncpg.Connection, page_size: int) -> int:
    return await conn.fetchval(
        "INSERT INTO sync_runs (status, page_size) VALUES ('running', $1) RETURNING id;",
        page_size,
    )


async def finish_sync_run(
    conn: asyncpg.Connection,
    sync_run_id: int,
    status: str,
    pages_processed: int,
    rows_received: int,
    projects_upserted: int,
    participants_upserted: int,
    error_summary: str | None = None,
    ) -> None:
    await conn.execute(
        """
        UPDATE sync_runs
        SET status = $2, finished_at = NOW(), pages_processed = $3, rows_received = $4,
            projects_upserted = $5, participants_upserted = $6, error_summary = $7
        WHERE id = $1;
        """,
        sync_run_id, status, pages_processed, rows_received, projects_upserted, participants_upserted, error_summary,
    )


async def deactivate_stale_permissions(conn: asyncpg.Connection, sync_run_id: int) -> None:
    await conn.execute(
        """
        UPDATE project_edit_permissions
        SET is_active = FALSE, updated_at = NOW()
        WHERE is_active = TRUE
          AND granted_by_sync_run_id IS DISTINCT FROM $1;
        """,
        sync_run_id,
    )


async def upsert_project_bundle(
    conn: asyncpg.Connection,
    sync_run_id: int,
    project: dict,
    participation: dict,
) -> tuple[int, int]:
    project_id = await conn.fetchval(
        """
        INSERT INTO projects (sie_project_id, process_code, title, source_summary, source_status, source_type,
            source_classification_id, source_thematic_area, source_research_chamber, has_external_funding,
            ethics_committee, sisgen_code, registered_on, starts_at, ends_at, source_updated_on,
            first_seen_sync_run_id, last_seen_sync_run_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$17)
        ON CONFLICT (sie_project_id) DO UPDATE SET
          process_code=EXCLUDED.process_code, title=EXCLUDED.title, source_summary=EXCLUDED.source_summary,
          source_status=EXCLUDED.source_status, source_type=EXCLUDED.source_type,
          source_classification_id=EXCLUDED.source_classification_id, source_thematic_area=EXCLUDED.source_thematic_area,
          source_research_chamber=EXCLUDED.source_research_chamber, has_external_funding=EXCLUDED.has_external_funding,
          ethics_committee=EXCLUDED.ethics_committee, sisgen_code=EXCLUDED.sisgen_code,
          registered_on=EXCLUDED.registered_on, starts_at=EXCLUDED.starts_at, ends_at=EXCLUDED.ends_at,
          source_updated_on=EXCLUDED.source_updated_on, last_seen_sync_run_id=EXCLUDED.last_seen_sync_run_id,
          updated_at=NOW()
        RETURNING id;
        """,
        project["sie_project_id"], project["process_code"], project["title"], project["source_summary"],
        project["source_status"], project["source_type"], project["source_classification_id"],
        project["source_thematic_area"], project["source_research_chamber"], project["has_external_funding"],
        project["ethics_committee"], project["sisgen_code"], project["registered_on"], project["starts_at"],
        project["ends_at"], project["source_updated_on"], sync_run_id,
    )
    person_id = await conn.fetchval(
        """
        INSERT INTO people (source_identity_key, cpf, full_name, institutional_email, profile,
            first_seen_sync_run_id, last_seen_sync_run_id)
        VALUES ($1,$2,$3,$4,$5,$6,$6)
        ON CONFLICT (source_identity_key) DO UPDATE SET full_name=EXCLUDED.full_name,
          institutional_email=COALESCE(EXCLUDED.institutional_email, people.institutional_email),
          profile=CASE WHEN EXCLUDED.profile='professor' THEN 'professor'
                       WHEN people.profile='professor' THEN 'professor'
                       WHEN EXCLUDED.profile='tecnico' THEN 'tecnico' ELSE people.profile END,
          last_seen_sync_run_id=EXCLUDED.last_seen_sync_run_id, updated_at=NOW()
        RETURNING id;
        """,
        participation["source_identity_key"], participation["cpf"], participation["full_name"],
        participation["institutional_email"], participation["profile"], sync_run_id,
    )
    await conn.execute(
        """
        UPDATE users
        SET role = people.profile, updated_at = NOW()
        FROM people
        WHERE people.id = $1
          AND users.id = people.user_id
          AND users.role <> people.profile;
        """,
        person_id,
    )
    await conn.execute(
        """
        INSERT INTO project_participations (project_id, person_id, participant_function, scholarship_type,
          participation_status, degree, project_email, standard_email, mobile_phone, landline_phone, weekly_hours,
          institutional_link, admission_method, job_description, work_schedule, departure_method, contract_status,
          possession_on, joined_on, left_on, participation_starts_on, participation_ends_on,
          first_seen_sync_run_id, last_seen_sync_run_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$23)
        ON CONFLICT (project_id, person_id, participant_function) DO UPDATE SET
          scholarship_type=EXCLUDED.scholarship_type, participation_status=EXCLUDED.participation_status,
          degree=EXCLUDED.degree, project_email=EXCLUDED.project_email, standard_email=EXCLUDED.standard_email,
          mobile_phone=EXCLUDED.mobile_phone, landline_phone=EXCLUDED.landline_phone, weekly_hours=EXCLUDED.weekly_hours,
          institutional_link=EXCLUDED.institutional_link, admission_method=EXCLUDED.admission_method,
          job_description=EXCLUDED.job_description, work_schedule=EXCLUDED.work_schedule,
          departure_method=EXCLUDED.departure_method, contract_status=EXCLUDED.contract_status,
          possession_on=EXCLUDED.possession_on, joined_on=EXCLUDED.joined_on, left_on=EXCLUDED.left_on,
          participation_starts_on=EXCLUDED.participation_starts_on, participation_ends_on=EXCLUDED.participation_ends_on,
          last_seen_sync_run_id=EXCLUDED.last_seen_sync_run_id, updated_at=NOW();
        """,
        project_id, person_id, participation["participant_function"], participation["scholarship_type"],
        participation["participation_status"], participation["degree"], participation["project_email"],
        participation["standard_email"], participation["mobile_phone"], participation["landline_phone"],
        participation["weekly_hours"], participation["institutional_link"], participation["admission_method"],
        participation["job_description"], participation["work_schedule"], participation["departure_method"],
        participation["contract_status"], participation["possession_on"], participation["joined_on"],
        participation["left_on"], participation["participation_starts_on"], participation["participation_ends_on"], sync_run_id,
    )
    if participation["permission_source"]:
        await conn.execute(
            """INSERT INTO project_edit_permissions (project_id, person_id, permission_source, granted_by_sync_run_id)
               VALUES ($1,$2,$3,$4) ON CONFLICT (project_id, person_id, permission_source)
               DO UPDATE SET is_active=TRUE, granted_by_sync_run_id=EXCLUDED.granted_by_sync_run_id, updated_at=NOW();""",
            project_id, person_id, participation["permission_source"], sync_run_id,
        )
    return project_id, person_id
