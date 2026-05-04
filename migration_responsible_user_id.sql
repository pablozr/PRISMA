BEGIN;

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS users_role_check;

ALTER TABLE users
  ADD CONSTRAINT users_role_check
  CHECK (role IN ('admin', 'professor', 'tecnico'));

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS responsible_user_id BIGINT REFERENCES users(id);

UPDATE projects p
SET responsible_user_id = pr.user_id
FROM professor_registry pr
WHERE p.responsible_user_id IS NULL
  AND p.owner_professor_id = pr.id
  AND pr.user_id IS NOT NULL;

ALTER TABLE projects
  ALTER COLUMN responsible_user_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_projects_responsible_user
  ON projects(responsible_user_id);

DROP INDEX IF EXISTS idx_projects_owner_professor;

ALTER TABLE projects
  DROP COLUMN IF EXISTS owner_professor_id;

COMMIT;
