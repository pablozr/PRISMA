CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Contas só existem depois do primeiro login Google. A pessoa importada
-- pelo SIE fica em people até então.
CREATE TABLE users (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  institutional_email CITEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'professor', 'tecnico', 'aluno')),
  role_source TEXT NOT NULL DEFAULT 'google_default'
    CHECK (role_source IN ('google_default', 'sie', 'admin')),
  password_hash TEXT,
  google_sub TEXT UNIQUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (password_hash IS NOT NULL OR google_sub IS NOT NULL),
  CHECK (role <> 'admin' OR role_source = 'admin')
);

-- Cada execução representa a atualização quinzenal da base local.
CREATE TABLE sync_runs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source TEXT NOT NULL DEFAULT 'sie_api',
  status TEXT NOT NULL CHECK (status IN ('running', 'success', 'partial', 'failed')),
  is_complete BOOLEAN NOT NULL DEFAULT FALSE,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  page_size INTEGER NOT NULL CHECK (page_size > 0),
  pages_processed INTEGER NOT NULL DEFAULT 0 CHECK (pages_processed >= 0),
  rows_received INTEGER NOT NULL DEFAULT 0 CHECK (rows_received >= 0),
  projects_upserted INTEGER NOT NULL DEFAULT 0 CHECK (projects_upserted >= 0),
  participants_upserted INTEGER NOT NULL DEFAULT 0 CHECK (participants_upserted >= 0),
  payload_hash TEXT,
  error_summary TEXT
);

-- Centro e unidade responsável recebidos do SIE; a hierarquia permite
-- centro -> unidade sem repetir texto em cada projeto.
CREATE TABLE organizational_units (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL,
  unit_type TEXT NOT NULL CHECK (unit_type IN ('centro', 'unidade')),
  parent_unit_id BIGINT REFERENCES organizational_units(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (name, unit_type, parent_unit_id)
);

-- Pessoa institucional importada. source_identity_key é calculada pelo
-- sincronizador a partir dos identificadores SIE disponíveis e evita duplicação.
CREATE TABLE people (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_identity_key TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  institutional_email CITEXT UNIQUE,
  profile TEXT NOT NULL CHECK (profile IN ('professor', 'tecnico', 'aluno')),
  user_id BIGINT UNIQUE REFERENCES users(id),
  first_seen_sync_run_id BIGINT REFERENCES sync_runs(id),
  last_seen_sync_run_id BIGINT REFERENCES sync_runs(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Projeto institucional e catálogo local são o mesmo agregado: os campos
-- source_* pertencem ao SIE; os campos local_* pertencem exclusivamente ao PRISMA.
CREATE TABLE projects (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sie_project_id BIGINT NOT NULL UNIQUE,
  process_code TEXT,
  title TEXT NOT NULL,
  source_summary TEXT,
  local_short_description TEXT,
  local_description TEXT,
  center_id BIGINT REFERENCES organizational_units(id),
  executing_unit_id BIGINT REFERENCES organizational_units(id),
  source_status TEXT,
  source_type TEXT,
  source_classification_id INTEGER,
  source_thematic_area TEXT,
  source_research_chamber TEXT,
  has_external_funding BOOLEAN,
  ethics_committee TEXT,
  sisgen_code TEXT,
  registered_on DATE,
  starts_at DATE,
  ends_at DATE,
  source_updated_on DATE,
  first_seen_sync_run_id BIGINT REFERENCES sync_runs(id),
  last_seen_sync_run_id BIGINT REFERENCES sync_runs(id),
  publication_status TEXT NOT NULL DEFAULT 'draft'
    CHECK (publication_status IN ('draft', 'published', 'archived')),
  is_visible BOOLEAN NOT NULL DEFAULT FALSE,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at)
);

CREATE TABLE project_keywords (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  position SMALLINT NOT NULL CHECK (position BETWEEN 1 AND 4),
  keyword TEXT NOT NULL,
  PRIMARY KEY (project_id, position)
);

CREATE INDEX idx_projects_description_trgm ON projects USING gin ((COALESCE(local_short_description, source_summary)) gin_trgm_ops);

-- Participação recebida do SIE. project_assignments não é reutilizada:
-- participação representa pessoa/vínculo; oportunidade é conteúdo local.
CREATE TABLE project_participations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  person_id BIGINT NOT NULL REFERENCES people(id),
  source_fingerprint TEXT NOT NULL,
  participant_function TEXT NOT NULL,
  scholarship_type TEXT,
  participation_status TEXT,
  degree TEXT,
  weekly_hours INTEGER CHECK (weekly_hours >= 0),
  institutional_link TEXT,
  admission_method TEXT,
  job_description TEXT,
  work_schedule TEXT,
  departure_method TEXT,
  contract_status TEXT,
  possession_on DATE,
  joined_on DATE,
  left_on DATE,
  participation_starts_on DATE,
  participation_ends_on DATE,
  first_seen_sync_run_id BIGINT REFERENCES sync_runs(id),
  last_seen_sync_run_id BIGINT REFERENCES sync_runs(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (project_id, source_fingerprint)
);

CREATE INDEX idx_project_participations_active ON project_participations (project_id, person_id) WHERE is_active;

-- Permissão por projeto derivada da regra de negócio importada do SIE.
-- Coordenador edita projeto coordenado; servidor edita projeto participado.
CREATE TABLE project_edit_permissions (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  person_id BIGINT NOT NULL REFERENCES people(id) ON DELETE CASCADE,
  permission_source TEXT NOT NULL CHECK (permission_source IN ('coordinator', 'server_participant')),
  granted_by_sync_run_id BIGINT REFERENCES sync_runs(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (project_id, person_id, permission_source)
);

-- Dados adicionais exclusivos do PRISMA.
CREATE TABLE project_images (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  image_type TEXT NOT NULL CHECK (image_type IN ('cover', 'gallery')),
  image_url TEXT NOT NULL,
  alt_text TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_project_cover
  ON project_images(project_id) WHERE image_type = 'cover';

CREATE TABLE project_areas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE
);

CREATE TABLE project_area_links (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  area_id BIGINT NOT NULL REFERENCES project_areas(id),
  PRIMARY KEY (project_id, area_id)
);

CREATE TABLE courses (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL,
  code TEXT UNIQUE,
  offering_unit_id BIGINT REFERENCES organizational_units(id),
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE project_course_links (
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  course_id BIGINT NOT NULL REFERENCES courses(id),
  PRIMARY KEY (project_id, course_id)
);

CREATE TABLE project_opportunities (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE project_opportunity_courses (
  opportunity_id BIGINT NOT NULL REFERENCES project_opportunities(id) ON DELETE CASCADE,
  course_id BIGINT NOT NULL REFERENCES courses(id),
  PRIMARY KEY (opportunity_id, course_id)
);

CREATE INDEX idx_projects_public_catalog
  ON projects(is_visible, publication_status, published_at DESC);
CREATE INDEX idx_projects_title_trgm
  ON projects USING gin (title gin_trgm_ops);
CREATE INDEX idx_projects_center ON projects(center_id);
CREATE INDEX idx_projects_unit ON projects(executing_unit_id);
CREATE INDEX idx_people_user ON people(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_participations_project ON project_participations(project_id);
CREATE INDEX idx_participations_person ON project_participations(person_id);
CREATE INDEX idx_participations_function ON project_participations(project_id, participant_function);
CREATE INDEX idx_project_permissions_person
  ON project_edit_permissions(person_id, project_id) WHERE is_active;
CREATE INDEX idx_project_area_links_area ON project_area_links(area_id);
CREATE INDEX idx_project_course_links_course ON project_course_links(course_id);
CREATE INDEX idx_project_opportunities_project
  ON project_opportunities(project_id, is_active, sort_order);
