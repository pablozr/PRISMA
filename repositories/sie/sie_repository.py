import hashlib
import re
import unicodedata

import asyncpg


async def create_sync_run(conn: asyncpg.Connection, page_size: int, source: str) -> int:
    return await conn.fetchval(
        "INSERT INTO sync_runs (status, source, page_size, is_complete) VALUES ('running', $1, $2, FALSE) RETURNING id;",
        source, page_size,
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
    is_complete: bool = False,
    ) -> None:
    await conn.execute(
        """
        UPDATE sync_runs
        SET status = $2, finished_at = NOW(), pages_processed = $3, rows_received = $4,
            projects_upserted = $5, participants_upserted = $6, error_summary = $7,
            is_complete = $8
        WHERE id = $1;
        """,
        sync_run_id, status, pages_processed, rows_received, projects_upserted, participants_upserted,
        error_summary, is_complete,
    )


async def _upsert_unit(
    conn: asyncpg.Connection, name: str | None, unit_type: str, parent_unit_id: int | None = None
) -> int | None:
    if not name:
        return None
    normalized_name = name.strip()
    if not normalized_name:
        return None
    existing = await conn.fetchval(
        """SELECT id FROM organizational_units
           WHERE name=$1 AND unit_type=$2 AND parent_unit_id IS NOT DISTINCT FROM $3""",
        normalized_name, unit_type, parent_unit_id,
    )
    if existing:
        return existing
    return await conn.fetchval(
        """INSERT INTO organizational_units(name, unit_type, parent_unit_id)
           VALUES($1,$2,$3) RETURNING id""",
        normalized_name, unit_type, parent_unit_id,
    )


async def upsert_project_bundle(
    conn: asyncpg.Connection,
    sync_run_id: int,
    project: dict,
    participation: dict,
) -> tuple[int, int]:
    center_id = await _upsert_unit(conn, project["center_name"], "centro")
    executing_unit_id = await _upsert_unit(
        conn, project["executing_unit_name"], "unidade", center_id
    )
    project_id = await conn.fetchval(
        """
        INSERT INTO projects (sie_project_id, process_code, title, source_summary, source_status, source_type,
            source_classification_id, source_thematic_area, source_research_chamber, has_external_funding,
            ethics_committee, sisgen_code, registered_on, starts_at, ends_at, source_updated_on,
            center_id, executing_unit_id, first_seen_sync_run_id, last_seen_sync_run_id,
            publication_status, is_visible, published_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$19,
            'published', TRUE, NOW())
        ON CONFLICT (sie_project_id) DO UPDATE SET
          process_code=EXCLUDED.process_code, title=EXCLUDED.title, source_summary=EXCLUDED.source_summary,
          source_status=EXCLUDED.source_status, source_type=EXCLUDED.source_type,
          source_classification_id=EXCLUDED.source_classification_id, source_thematic_area=EXCLUDED.source_thematic_area,
          source_research_chamber=EXCLUDED.source_research_chamber, has_external_funding=EXCLUDED.has_external_funding,
          ethics_committee=EXCLUDED.ethics_committee, sisgen_code=EXCLUDED.sisgen_code,
          registered_on=EXCLUDED.registered_on, starts_at=EXCLUDED.starts_at, ends_at=EXCLUDED.ends_at,
           center_id=EXCLUDED.center_id, executing_unit_id=EXCLUDED.executing_unit_id,
           source_updated_on=EXCLUDED.source_updated_on, last_seen_sync_run_id=EXCLUDED.last_seen_sync_run_id,
           publication_status='published', is_visible=TRUE,
           published_at=COALESCE(projects.published_at, NOW()),
           updated_at=NOW()
        RETURNING id;
        """,
        project["sie_project_id"], project["process_code"], project["title"], project["source_summary"],
        project["source_status"], project["source_type"], project["source_classification_id"],
        project["source_thematic_area"], project["source_research_chamber"], project["has_external_funding"],
        project["ethics_committee"], project["sisgen_code"], project["registered_on"], project["starts_at"],
        project["ends_at"], project["source_updated_on"], center_id, executing_unit_id, sync_run_id,
    )
    await conn.execute("DELETE FROM project_keywords WHERE project_id=$1", project_id)
    await conn.executemany(
        "INSERT INTO project_keywords(project_id, position, keyword) VALUES($1,$2,$3)",
        [(project_id, position, keyword.strip()) for position, keyword in enumerate(project["keywords"], 1) if keyword and keyword.strip()],
    )
    if project["source_thematic_area"]:
        area_name = project["source_thematic_area"]
        slug_base = re.sub(
            r"[^a-z0-9]+",
            "-",
            unicodedata.normalize("NFKD", area_name).encode("ascii", "ignore").decode().lower(),
        ).strip("-")
        area_id = await conn.fetchval(
            """INSERT INTO project_areas(name, slug) VALUES($1,$2)
               ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name RETURNING id""",
            area_name,
            f"{slug_base or 'area'}-{hashlib.sha256(area_name.encode()).hexdigest()[:8]}",
        )
        await conn.execute(
            "INSERT INTO project_area_links(project_id, area_id) VALUES($1,$2) ON CONFLICT DO NOTHING",
            project_id,
            area_id,
        )
    person_id = await conn.fetchval(
        """SELECT id FROM people
           WHERE source_identity_key=$1
               OR ($2::CITEXT IS NOT NULL AND institutional_email=$2)
            LIMIT 1""",
        participation["source_identity_key"], participation["institutional_email"],
    )
    if person_id:
        await conn.execute(
            """UPDATE people SET full_name=$2,
                  institutional_email=COALESCE(institutional_email,$3),
                  profile=CASE WHEN $4='professor' THEN 'professor'
                               WHEN profile='professor' THEN 'professor'
                               WHEN $4='tecnico' THEN 'tecnico' ELSE profile END,
                  last_seen_sync_run_id=$5, updated_at=NOW() WHERE id=$1""",
            person_id, participation["full_name"], participation["institutional_email"], participation["profile"], sync_run_id,
        )
    else:
        person_id = await conn.fetchval(
        """
        INSERT INTO people (source_identity_key, full_name, institutional_email, profile,
            first_seen_sync_run_id, last_seen_sync_run_id)
        VALUES ($1,$2,$3,$4,$5,$5)
        ON CONFLICT (source_identity_key) DO UPDATE SET full_name=EXCLUDED.full_name,
          institutional_email=COALESCE(EXCLUDED.institutional_email, people.institutional_email),
          profile=CASE WHEN EXCLUDED.profile='professor' THEN 'professor'
                       WHEN people.profile='professor' THEN 'professor'
                       WHEN EXCLUDED.profile='tecnico' THEN 'tecnico' ELSE people.profile END,
          last_seen_sync_run_id=EXCLUDED.last_seen_sync_run_id, updated_at=NOW()
        RETURNING id;
        """,
            participation["source_identity_key"], participation["full_name"], participation["institutional_email"],
            participation["profile"], sync_run_id,
        )
    if participation["institutional_email"]:
        await conn.execute(
            """UPDATE people SET user_id = user_account.id, updated_at = NOW()
               FROM users user_account
               WHERE people.id = $1
                 AND people.user_id IS NULL
                 AND user_account.institutional_email = $2
                 AND user_account.is_active = TRUE""",
            person_id,
            participation["institutional_email"],
        )
    await conn.execute(
        """
        UPDATE users
        SET role = CASE
              WHEN people.profile = 'professor' THEN 'professor'
              WHEN people.profile = 'tecnico' AND users.role = 'aluno' THEN 'tecnico'
              ELSE users.role
            END,
            role_source = CASE
              WHEN people.profile IN ('professor', 'tecnico') THEN 'sie'
              ELSE users.role_source
            END,
            updated_at = NOW()
        FROM people
        WHERE people.id = $1
          AND users.id = people.user_id
          AND users.role <> 'admin'
          AND users.role_source <> 'admin'
          AND (people.profile = 'professor' OR (people.profile = 'tecnico' AND users.role = 'aluno'));
        """,
        person_id,
    )
    await conn.execute(
        """
        INSERT INTO project_participations (project_id, person_id, source_fingerprint, participant_function, scholarship_type,
          participation_status, degree, weekly_hours,
          institutional_link, admission_method, job_description, work_schedule, departure_method, contract_status,
          possession_on, joined_on, left_on, participation_starts_on, participation_ends_on,
          first_seen_sync_run_id, last_seen_sync_run_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$20)
        ON CONFLICT (project_id, source_fingerprint) DO UPDATE SET
           person_id=EXCLUDED.person_id, participant_function=EXCLUDED.participant_function,
           scholarship_type=EXCLUDED.scholarship_type, participation_status=EXCLUDED.participation_status,
           degree=EXCLUDED.degree, weekly_hours=EXCLUDED.weekly_hours,
          institutional_link=EXCLUDED.institutional_link, admission_method=EXCLUDED.admission_method,
          job_description=EXCLUDED.job_description, work_schedule=EXCLUDED.work_schedule,
          departure_method=EXCLUDED.departure_method, contract_status=EXCLUDED.contract_status,
          possession_on=EXCLUDED.possession_on, joined_on=EXCLUDED.joined_on, left_on=EXCLUDED.left_on,
          participation_starts_on=EXCLUDED.participation_starts_on, participation_ends_on=EXCLUDED.participation_ends_on,
          last_seen_sync_run_id=EXCLUDED.last_seen_sync_run_id, is_active=TRUE, updated_at=NOW();
        """,
        project_id, person_id, participation["participation_fingerprint"], participation["participant_function"], participation["scholarship_type"],
        participation["participation_status"], participation["degree"], participation["weekly_hours"],
        participation["institutional_link"], participation["admission_method"],
        participation["job_description"], participation["work_schedule"], participation["departure_method"],
        participation["contract_status"], participation["possession_on"], participation["joined_on"],
        participation["left_on"], participation["participation_starts_on"], participation["participation_ends_on"], sync_run_id,
    )
    # A person without an institutional email cannot be linked by the Google
    # login flow, so an SIE-only identity must never create usable access.
    if participation["institutional_email"] and participation["permission_source"]:
        await conn.execute(
            """INSERT INTO project_edit_permissions (project_id, person_id, permission_source, granted_by_sync_run_id)
               VALUES ($1,$2,$3,$4) ON CONFLICT (project_id, person_id, permission_source)
               DO UPDATE SET is_active=TRUE, granted_by_sync_run_id=EXCLUDED.granted_by_sync_run_id, updated_at=NOW();""",
            project_id, person_id, participation["permission_source"], sync_run_id,
        )
    return project_id, person_id
