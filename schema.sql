CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  institutional_email CITEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'student', 'professor')),
  password_hash TEXT,
  google_sub TEXT UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (password_hash IS NOT NULL OR google_sub IS NOT NULL)
);

CREATE TABLE import_batches (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  reference_year SMALLINT NOT NULL,
  reference_term SMALLINT NOT NULL CHECK (reference_term IN (1, 2)),
  uploaded_by_user_id BIGINT NOT NULL REFERENCES users(id),
  source_filename TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('processing', 'success', 'partial', 'failed')),
  total_rows INTEGER NOT NULL DEFAULT 0,
  imported_rows INTEGER NOT NULL DEFAULT 0,
  rejected_rows INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE organizational_units (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL,
  short_name TEXT,
  type TEXT NOT NULL CHECK (type IN ('centro', 'departamento', 'instituto')),
  parent_unit_id BIGINT REFERENCES organizational_units(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE professor_registry (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  institutional_email CITEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  siape TEXT UNIQUE,
  unit_id BIGINT REFERENCES organizational_units(id),
  user_id BIGINT UNIQUE REFERENCES users(id),
  source_import_batch_id BIGINT REFERENCES import_batches(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE student_registry (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  institutional_email CITEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  registration_number TEXT UNIQUE,
  course_id BIGINT REFERENCES courses(id),
  user_id BIGINT UNIQUE REFERENCES users(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE projects (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  process_code TEXT,
  title TEXT NOT NULL,
  short_description TEXT,
  full_description TEXT,
  contact_email CITEXT NOT NULL,
  owner_professor_id BIGINT NOT NULL REFERENCES professor_registry(id),
  executing_unit_id BIGINT REFERENCES organizational_units(id),
  source_import_batch_id BIGINT REFERENCES import_batches(id),
  status TEXT NOT NULL CHECK (status IN ('draft', 'published', 'archived')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  starts_at DATE,
  ends_at DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  published_at TIMESTAMPTZ,
  deactivated_at TIMESTAMPTZ,
  CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at)
);

CREATE TABLE project_images (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  image_type TEXT NOT NULL CHECK (image_type IN ('cover', 'gallery')),
  image_url TEXT NOT NULL,
  alt_text TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_project_single_cover
  ON project_images(project_id)
  WHERE image_type = 'cover';

CREATE TABLE courses (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  unit_id BIGINT REFERENCES organizational_units(id),
  name TEXT NOT NULL,
  level TEXT NOT NULL CHECK (level IN ('graduacao', 'pos')),
  code TEXT UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE project_areas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE project_area_links (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  area_id BIGINT NOT NULL REFERENCES project_areas(id),
  PRIMARY KEY (project_id, area_id)
);

CREATE TABLE project_course_links (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  course_id BIGINT NOT NULL REFERENCES courses(id),
  PRIMARY KEY (project_id, course_id)
);

CREATE TABLE import_row_errors (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  import_batch_id BIGINT NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  raw_payload JSONB NOT NULL,
  error_reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE project_import_links (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  import_batch_id BIGINT NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (project_id, import_batch_id)
);

CREATE TABLE project_change_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  changed_by_user_id BIGINT NOT NULL REFERENCES users(id),
  change_type TEXT NOT NULL CHECK (change_type IN ('manual_edit', 'status_change', 'import_override')),
  field_name TEXT NOT NULL,
  old_value JSONB,
  new_value JSONB,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE email_dispatch_requests (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  requested_by_user_id BIGINT NOT NULL REFERENCES users(id),
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  to_email CITEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  payload JSONB,
  status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'sent', 'failed', 'dead_letter')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  next_attempt_at TIMESTAMPTZ,
  last_error TEXT,
  provider_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at TIMESTAMPTZ
);

CREATE TABLE ai_chat_sessions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  title TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_chat_messages (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_sql_suggestions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES users(id),
  question TEXT NOT NULL,
  generated_sql TEXT NOT NULL,
  validation_status TEXT NOT NULL CHECK (validation_status IN ('approved', 'rejected')),
  validation_errors JSONB,
  model_name TEXT,
  feedback_score SMALLINT CHECK (feedback_score BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_projects_public_listing
  ON projects(is_active, status, published_at DESC);

CREATE INDEX idx_projects_title_trgm
  ON projects USING gin (title gin_trgm_ops);

CREATE INDEX idx_projects_owner_professor
  ON projects(owner_professor_id);

CREATE INDEX idx_projects_executing_unit
  ON projects(executing_unit_id);

CREATE INDEX idx_org_units_parent
  ON organizational_units(parent_unit_id);

CREATE INDEX idx_courses_unit
  ON courses(unit_id);

CREATE INDEX idx_project_area_links_area
  ON project_area_links(area_id);

CREATE INDEX idx_project_course_links_course
  ON project_course_links(course_id);

CREATE INDEX idx_import_batches_ref
  ON import_batches(reference_year, reference_term);

CREATE INDEX idx_import_row_errors_batch_row
  ON import_row_errors(import_batch_id, row_number);

CREATE INDEX idx_project_import_links_batch
  ON project_import_links(import_batch_id);

CREATE INDEX idx_project_change_logs_project_created
  ON project_change_logs(project_id, created_at DESC);

CREATE INDEX idx_project_change_logs_user_created
  ON project_change_logs(changed_by_user_id, created_at DESC);

CREATE INDEX idx_email_dispatch_status_next
  ON email_dispatch_requests(status, next_attempt_at);

CREATE INDEX idx_email_dispatch_user_created
  ON email_dispatch_requests(requested_by_user_id, created_at DESC);

CREATE INDEX idx_ai_sessions_user_created
  ON ai_chat_sessions(user_id, created_at DESC);

CREATE INDEX idx_ai_messages_session_created
  ON ai_chat_messages(session_id, created_at DESC);

CREATE INDEX idx_ai_sql_suggestions_user_created
  ON ai_sql_suggestions(user_id, created_at DESC);
