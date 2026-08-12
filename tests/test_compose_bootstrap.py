from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_compose_bootstrap_applies_sie_sync_safety_migration_after_schema() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    migration = (ROOT / "migration_sie_sync_safety.sql").read_text(encoding="utf-8")

    assert "./migration_sie_sync_safety.sql:/migration_sie_sync_safety.sql:ro" in compose
    assert "-f /schema.sql" in compose
    assert "-f /migration_sie_sync_safety.sql" in compose
    assert compose.index("-f /schema.sql") < compose.index("-f /migration_sie_sync_safety.sql")
    assert "ADD COLUMN IF NOT EXISTS" in migration
    assert "DROP COLUMN IF EXISTS" in migration
