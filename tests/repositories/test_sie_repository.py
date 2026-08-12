import asyncio

from repositories.sie.sie_repository import upsert_project_bundle


class Connection:
    def __init__(self) -> None:
        self.executed: list[str] = []

    async def fetchval(self, query: str, *args):
        if "INSERT INTO projects" in query:
            return 1
        if "INSERT INTO project_areas" in query:
            return 3
        if "SELECT id FROM people" in query:
            return 2
        raise AssertionError(query)

    async def execute(self, query: str, *args) -> None:
        self.executed.append(query)

    async def executemany(self, query: str, args) -> None:
        self.executed.append(query)


def test_email_less_participant_does_not_receive_edit_permission() -> None:
    conn = Connection()
    project = {"center_name": None, "executing_unit_name": None, "sie_project_id": 1, "process_code": None,
               "title": "Projeto", "source_summary": None, "source_status": None, "source_type": None,
               "source_classification_id": None, "source_thematic_area": None, "source_research_chamber": None,
               "has_external_funding": None, "ethics_committee": None, "sisgen_code": None, "registered_on": None,
               "starts_at": None, "ends_at": None, "source_updated_on": None, "keywords": []}
    participation = {"source_identity_key": "identity", "institutional_email": None, "full_name": "Ana",
                     "profile": "professor", "participation_fingerprint": "fingerprint",
                     "participant_function": "Coordenador", "permission_source": "coordinator",
                     "scholarship_type": None, "participation_status": None, "degree": None, "weekly_hours": None,
                     "institutional_link": None, "admission_method": None, "job_description": None,
                     "work_schedule": None, "departure_method": None, "contract_status": None, "possession_on": None,
                     "joined_on": None, "left_on": None, "participation_starts_on": None,
                     "participation_ends_on": None}

    asyncio.run(upsert_project_bundle(conn, 1, project, participation))

    assert all("INSERT INTO project_edit_permissions" not in query for query in conn.executed)


def test_sie_thematic_area_is_added_to_the_catalogue_and_linked_to_the_project() -> None:
    conn = Connection()
    project = {"center_name": None, "executing_unit_name": None, "sie_project_id": 1, "process_code": None,
               "title": "Projeto", "source_summary": None, "source_status": None, "source_type": None,
               "source_classification_id": None, "source_thematic_area": "Saúde Coletiva", "source_research_chamber": None,
               "has_external_funding": None, "ethics_committee": None, "sisgen_code": None, "registered_on": None,
               "starts_at": None, "ends_at": None, "source_updated_on": None, "keywords": []}
    participation = {"source_identity_key": "identity", "institutional_email": None, "full_name": "Ana",
                     "profile": "professor", "participation_fingerprint": "fingerprint",
                     "participant_function": "Coordenador", "permission_source": None,
                     "scholarship_type": None, "participation_status": None, "degree": None, "weekly_hours": None,
                     "institutional_link": None, "admission_method": None, "job_description": None,
                     "work_schedule": None, "departure_method": None, "contract_status": None, "possession_on": None,
                     "joined_on": None, "left_on": None, "participation_starts_on": None,
                     "participation_ends_on": None}

    asyncio.run(upsert_project_bundle(conn, 1, project, participation))

    assert any("INSERT INTO project_area_links" in query for query in conn.executed)
