ALTER TABLE users
  ADD COLUMN IF NOT EXISTS role_source TEXT NOT NULL DEFAULT 'google_default';

UPDATE users u
SET role_source = 'admin'
WHERE u.role_source = 'google_default'
  AND u.role <> 'aluno';

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS users_role_source_check;

ALTER TABLE users
  ADD CONSTRAINT users_role_source_check
  CHECK (role_source IN ('google_default', 'sie', 'admin'));

ALTER TABLE users
  DROP CONSTRAINT IF EXISTS users_admin_role_source_check;

ALTER TABLE users
  ADD CONSTRAINT users_admin_role_source_check
  CHECK (role <> 'admin' OR role_source = 'admin');
