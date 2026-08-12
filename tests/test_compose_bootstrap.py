from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_compose_bootstrap_applies_sie_sync_safety_migration_after_schema() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    migration = (ROOT / "migration_sie_sync_safety.sql").read_text(encoding="utf-8")

    assert "./migration_sie_sync_safety.sql:/migration_sie_sync_safety.sql:ro" in compose
    assert "./migration_user_role_source.sql:/migration_user_role_source.sql:ro" in compose
    assert "-f /schema.sql" in compose
    assert "-f /migration_sie_sync_safety.sql" in compose
    assert compose.index("-f /schema.sql") < compose.index("-f /migration_sie_sync_safety.sql")
    assert compose.index("-f /migration_sie_publish_projects.sql") < compose.index("-f /migration_user_role_source.sql")
    assert "ADD COLUMN IF NOT EXISTS" in migration
    assert "DROP COLUMN IF EXISTS" in migration


def test_role_source_migration_preserves_existing_roles_as_admin_managed() -> None:
    migration = (ROOT / "migration_user_role_source.sql").read_text(encoding="utf-8")

    assert "SET role_source = 'admin'" in migration
    assert "u.role <> 'aluno'" in migration
    assert "users_admin_role_source_check" in migration
