BEGIN;

-- The existing source_identity_key and source_fingerprint values are the
-- backfill for rows that have a stable source identifier: keep their SHA-256
-- digests untouched while removing the raw CPF and phone columns below.
-- New rows must use the same digest input order (CPF, then e-mail); rows with
-- neither stable identifier are skipped rather than merged by name/function.

ALTER TABLE sync_runs
  ADD COLUMN IF NOT EXISTS source TEXT;

UPDATE sync_runs
SET source = 'sie_api'
WHERE source IS NULL;

ALTER TABLE sync_runs
  ALTER COLUMN source SET DEFAULT 'sie_api',
  ALTER COLUMN source SET NOT NULL,
  ADD COLUMN IF NOT EXISTS is_complete BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE people
  DROP COLUMN IF EXISTS cpf;

ALTER TABLE project_participations
  DROP COLUMN IF EXISTS project_email,
  DROP COLUMN IF EXISTS standard_email,
  DROP COLUMN IF EXISTS mobile_phone,
  DROP COLUMN IF EXISTS landline_phone;

COMMIT;
