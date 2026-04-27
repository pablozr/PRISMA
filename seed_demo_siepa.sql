-- =========================================================
-- SIEPA - Seed de demonstração para ambiente de visualização
-- ---------------------------------------------------------
-- Objetivo: popular dados fictícios para testar listagem,
-- detalhes, filtros, imagens, cursos, áreas e atribuições.
--
-- Seguro para rodar mais de uma vez:
-- - Não usa DELETE/TRUNCATE.
-- - Usa ON CONFLICT quando há constraints únicas.
-- - Para tabelas sem unique, consulta por nomes/códigos DEMO antes de inserir.
--
-- Dados fáceis de localizar:
-- - Emails: @demo.unirio.br
-- - Process codes: DEMO-SIEPA-...
-- - Import hash: demo-siepa-seed-v1
--
-- Atenção:
-- - O password_hash do admin é apenas placeholder. Troque pelo hash real
--   gerado pela sua aplicação se quiser login interno funcionando.
-- =========================================================

BEGIN;

-- Tipos de projeto base
INSERT INTO project_types (name, slug, is_enabled)
VALUES
  ('Extensao', 'extensao', TRUE),
  ('Iniciacao Cientifica', 'iniciacao_cientifica', TRUE)
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  is_enabled = EXCLUDED.is_enabled,
  updated_at = NOW();

-- Usuários demo
INSERT INTO users (institutional_email, full_name, role, password_hash, google_sub, is_active)
VALUES
  ('admin.demo@demo.unirio.br', 'Administrador Demo SIEPA', 'admin', '123', NULL, TRUE),
  ('ana.martins@demo.unirio.br', 'Ana Martins', 'professor', NULL, 'google-demo-prof-ana-martins', TRUE),
  ('bruno.costa@demo.unirio.br', 'Bruno Costa', 'professor', NULL, 'google-demo-prof-bruno-costa', TRUE),
  ('carla.souza@demo.unirio.br', 'Carla Souza', 'professor', NULL, 'google-demo-prof-carla-souza', TRUE),
  ('joao.aluno@demo.unirio.br', 'Joao Aluno Demo', 'student', NULL, 'google-demo-student-joao', TRUE)
ON CONFLICT (institutional_email) DO UPDATE SET
  full_name = EXCLUDED.full_name,
  role = EXCLUDED.role,
  password_hash = EXCLUDED.password_hash,
  google_sub = EXCLUDED.google_sub,
  is_active = EXCLUDED.is_active,
  updated_at = NOW();

DO $$
DECLARE
  v_admin_id BIGINT;
  v_batch_id BIGINT;

  v_ccet_id BIGINT;
  v_cch_id BIGINT;
  v_ccbs_id BIGINT;
  v_ibio_id BIGINT;
  v_eco_id BIGINT;
  v_ia_id BIGINT;
  v_ic_id BIGINT;

  v_prof_ana_id BIGINT;
  v_prof_bruno_id BIGINT;
  v_prof_carla_id BIGINT;

  v_extensao_id BIGINT;
  v_ic_type_id BIGINT;

  v_area_tecnologia BIGINT;
  v_area_educacao BIGINT;
  v_area_saude BIGINT;
  v_area_cultura BIGINT;
  v_area_meio_ambiente BIGINT;

  v_curso_si BIGINT;
  v_curso_bio BIGINT;
  v_curso_pedagogia BIGINT;
  v_curso_musica BIGINT;
  v_curso_enfermagem BIGINT;
  v_curso_mestrado_info BIGINT;

  v_project_1 BIGINT;
  v_project_2 BIGINT;
  v_project_3 BIGINT;
  v_project_4 BIGINT;
  v_project_5 BIGINT;
  v_project_6 BIGINT;

  v_assignment_id BIGINT;
BEGIN
  SELECT id INTO v_admin_id
  FROM users
  WHERE institutional_email = 'admin.demo@demo.unirio.br';

  SELECT id INTO v_batch_id
  FROM import_batches
  WHERE source_hash = 'demo-siepa-seed-v1'
  LIMIT 1;

  IF v_batch_id IS NULL THEN
    INSERT INTO import_batches (
      reference_year,
      reference_term,
      uploaded_by_user_id,
      source_filename,
      source_hash,
      status,
      total_rows,
      imported_rows,
      rejected_rows,
      finished_at
    )
    VALUES (
      2026,
      1,
      v_admin_id,
      'demo_siepa_seed.csv',
      'demo-siepa-seed-v1',
      'success',
      6,
      6,
      0,
      NOW()
    )
    RETURNING id INTO v_batch_id;
  END IF;

  -- Unidades organizacionais demo
  SELECT id INTO v_ccet_id FROM organizational_units WHERE name = 'DEMO - Centro de Ciencias Exatas e Tecnologia' LIMIT 1;
  IF v_ccet_id IS NULL THEN
    INSERT INTO organizational_units (name, short_name, type, parent_unit_id)
    VALUES ('DEMO - Centro de Ciencias Exatas e Tecnologia', 'DEMO-CCET', 'centro', NULL)
    RETURNING id INTO v_ccet_id;
  END IF;

  SELECT id INTO v_cch_id FROM organizational_units WHERE name = 'DEMO - Centro de Ciencias Humanas e Sociais' LIMIT 1;
  IF v_cch_id IS NULL THEN
    INSERT INTO organizational_units (name, short_name, type, parent_unit_id)
    VALUES ('DEMO - Centro de Ciencias Humanas e Sociais', 'DEMO-CCH', 'centro', NULL)
    RETURNING id INTO v_cch_id;
  END IF;

  SELECT id INTO v_ccbs_id FROM organizational_units WHERE name = 'DEMO - Centro de Ciencias Biologicas e da Saude' LIMIT 1;
  IF v_ccbs_id IS NULL THEN
    INSERT INTO organizational_units (name, short_name, type, parent_unit_id)
    VALUES ('DEMO - Centro de Ciencias Biologicas e da Saude', 'DEMO-CCBS', 'centro', NULL)
    RETURNING id INTO v_ccbs_id;
  END IF;

  SELECT id INTO v_ic_id FROM organizational_units WHERE name = 'DEMO - Instituto de Computacao' LIMIT 1;
  IF v_ic_id IS NULL THEN
    INSERT INTO organizational_units (name, short_name, type, parent_unit_id)
    VALUES ('DEMO - Instituto de Computacao', 'DEMO-IC', 'instituto', v_ccet_id)
    RETURNING id INTO v_ic_id;
  END IF;

  SELECT id INTO v_ibio_id FROM organizational_units WHERE name = 'DEMO - Instituto de Biociencias' LIMIT 1;
  IF v_ibio_id IS NULL THEN
    INSERT INTO organizational_units (name, short_name, type, parent_unit_id)
    VALUES ('DEMO - Instituto de Biociencias', 'DEMO-IBIO', 'instituto', v_ccbs_id)
    RETURNING id INTO v_ibio_id;
  END IF;

  SELECT id INTO v_eco_id FROM organizational_units WHERE name = 'DEMO - Escola de Educacao' LIMIT 1;
  IF v_eco_id IS NULL THEN
    INSERT INTO organizational_units (name, short_name, type, parent_unit_id)
    VALUES ('DEMO - Escola de Educacao', 'DEMO-EDU', 'instituto', v_cch_id)
    RETURNING id INTO v_eco_id;
  END IF;

  SELECT id INTO v_ia_id FROM organizational_units WHERE name = 'DEMO - Instituto de Artes' LIMIT 1;
  IF v_ia_id IS NULL THEN
    INSERT INTO organizational_units (name, short_name, type, parent_unit_id)
    VALUES ('DEMO - Instituto de Artes', 'DEMO-ARTES', 'instituto', v_cch_id)
    RETURNING id INTO v_ia_id;
  END IF;

  -- Cursos demo
  INSERT INTO courses (unit_id, name, level, code, is_active)
  VALUES
    (v_ic_id, 'DEMO - Sistemas de Informacao', 'graduacao', 'DEMO-SI', TRUE),
    (v_ic_id, 'DEMO - Mestrado em Informatica', 'pos', 'DEMO-PPGI', TRUE),
    (v_ibio_id, 'DEMO - Ciencias Biologicas', 'graduacao', 'DEMO-BIO', TRUE),
    (v_eco_id, 'DEMO - Pedagogia', 'graduacao', 'DEMO-PED', TRUE),
    (v_ia_id, 'DEMO - Musica', 'graduacao', 'DEMO-MUS', TRUE),
    (v_ccbs_id, 'DEMO - Enfermagem', 'graduacao', 'DEMO-ENF', TRUE)
  ON CONFLICT (code) DO UPDATE SET
    unit_id = EXCLUDED.unit_id,
    name = EXCLUDED.name,
    level = EXCLUDED.level,
    is_active = EXCLUDED.is_active;

  SELECT id INTO v_curso_si FROM courses WHERE code = 'DEMO-SI';
  SELECT id INTO v_curso_mestrado_info FROM courses WHERE code = 'DEMO-PPGI';
  SELECT id INTO v_curso_bio FROM courses WHERE code = 'DEMO-BIO';
  SELECT id INTO v_curso_pedagogia FROM courses WHERE code = 'DEMO-PED';
  SELECT id INTO v_curso_musica FROM courses WHERE code = 'DEMO-MUS';
  SELECT id INTO v_curso_enfermagem FROM courses WHERE code = 'DEMO-ENF';

  -- Professores demo
  INSERT INTO professor_registry (
    institutional_email,
    full_name,
    siape,
    unit_id,
    user_id,
    source_import_batch_id,
    is_active
  )
  VALUES
    ('ana.martins@demo.unirio.br', 'Ana Martins', 'DEMO-SIAPE-001', v_ic_id, (SELECT id FROM users WHERE institutional_email = 'ana.martins@demo.unirio.br'), v_batch_id, TRUE),
    ('bruno.costa@demo.unirio.br', 'Bruno Costa', 'DEMO-SIAPE-002', v_ibio_id, (SELECT id FROM users WHERE institutional_email = 'bruno.costa@demo.unirio.br'), v_batch_id, TRUE),
    ('carla.souza@demo.unirio.br', 'Carla Souza', 'DEMO-SIAPE-003', v_eco_id, (SELECT id FROM users WHERE institutional_email = 'carla.souza@demo.unirio.br'), v_batch_id, TRUE)
  ON CONFLICT (institutional_email) DO UPDATE SET
    full_name = EXCLUDED.full_name,
    siape = EXCLUDED.siape,
    unit_id = EXCLUDED.unit_id,
    user_id = EXCLUDED.user_id,
    source_import_batch_id = EXCLUDED.source_import_batch_id,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

  SELECT id INTO v_prof_ana_id FROM professor_registry WHERE institutional_email = 'ana.martins@demo.unirio.br';
  SELECT id INTO v_prof_bruno_id FROM professor_registry WHERE institutional_email = 'bruno.costa@demo.unirio.br';
  SELECT id INTO v_prof_carla_id FROM professor_registry WHERE institutional_email = 'carla.souza@demo.unirio.br';

  SELECT id INTO v_extensao_id FROM project_types WHERE slug = 'extensao';
  SELECT id INTO v_ic_type_id FROM project_types WHERE slug = 'iniciacao_cientifica';

  -- Áreas temáticas demo
  INSERT INTO project_areas (name, slug)
  VALUES
    ('DEMO - Tecnologia e Producao', 'demo-tecnologia-e-producao'),
    ('DEMO - Educacao', 'demo-educacao'),
    ('DEMO - Saude', 'demo-saude'),
    ('DEMO - Cultura', 'demo-cultura'),
    ('DEMO - Meio Ambiente', 'demo-meio-ambiente')
  ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name;

  SELECT id INTO v_area_tecnologia FROM project_areas WHERE slug = 'demo-tecnologia-e-producao';
  SELECT id INTO v_area_educacao FROM project_areas WHERE slug = 'demo-educacao';
  SELECT id INTO v_area_saude FROM project_areas WHERE slug = 'demo-saude';
  SELECT id INTO v_area_cultura FROM project_areas WHERE slug = 'demo-cultura';
  SELECT id INTO v_area_meio_ambiente FROM project_areas WHERE slug = 'demo-meio-ambiente';

  -- Projetos demo
  SELECT id INTO v_project_1 FROM projects WHERE process_code = 'DEMO-SIEPA-EXT-001' LIMIT 1;
  IF v_project_1 IS NULL THEN
    INSERT INTO projects (
      process_code,
      title,
      short_description,
      full_description,
      contact_email,
      owner_professor_id,
      executing_unit_id,
      source_import_batch_id,
      project_type_id,
      status,
      is_active,
      starts_at,
      ends_at,
      published_at
    )
    VALUES (
      'DEMO-SIEPA-EXT-001',
      'DEMO - Laboratorio Aberto de Tecnologia para a Comunidade',
      'Oficinas introdutorias de tecnologia, cidadania digital e desenvolvimento web para a comunidade externa.',
      'Projeto de extensao voltado para aproximar estudantes, professores e comunidade externa por meio de oficinas praticas sobre tecnologia, cidadania digital, programacao introdutoria e boas praticas de uso da internet.',
      'ana.martins@demo.unirio.br',
      v_prof_ana_id,
      v_ic_id,
      v_batch_id,
      v_extensao_id,
      'published',
      TRUE,
      DATE '2026-03-01',
      DATE '2026-12-15',
      NOW() - INTERVAL '18 days'
    )
    RETURNING id INTO v_project_1;
  ELSE
    UPDATE projects SET
      title = 'DEMO - Laboratorio Aberto de Tecnologia para a Comunidade',
      short_description = 'Oficinas introdutorias de tecnologia, cidadania digital e desenvolvimento web para a comunidade externa.',
      full_description = 'Projeto de extensao voltado para aproximar estudantes, professores e comunidade externa por meio de oficinas praticas sobre tecnologia, cidadania digital, programacao introdutoria e boas praticas de uso da internet.',
      contact_email = 'ana.martins@demo.unirio.br',
      owner_professor_id = v_prof_ana_id,
      executing_unit_id = v_ic_id,
      source_import_batch_id = v_batch_id,
      project_type_id = v_extensao_id,
      status = 'published',
      is_active = TRUE,
      starts_at = DATE '2026-03-01',
      ends_at = DATE '2026-12-15',
      published_at = COALESCE(published_at, NOW() - INTERVAL '18 days'),
      updated_at = NOW()
    WHERE id = v_project_1;
  END IF;

  SELECT id INTO v_project_2 FROM projects WHERE process_code = 'DEMO-SIEPA-IC-001' LIMIT 1;
  IF v_project_2 IS NULL THEN
    INSERT INTO projects (
      process_code, title, short_description, full_description, contact_email,
      owner_professor_id, executing_unit_id, source_import_batch_id, project_type_id,
      status, is_active, starts_at, ends_at, published_at
    )
    VALUES (
      'DEMO-SIEPA-IC-001',
      'DEMO - Modelos Inteligentes para Catalogos Academicos',
      'Pesquisa sobre organizacao, busca e recomendacao de projetos academicos em portais institucionais.',
      'Projeto de iniciacao cientifica que investiga formas de estruturar catalogos academicos, melhorar busca textual e apoiar recomendacoes de projetos conforme areas, cursos e unidades institucionais.',
      'ana.martins@demo.unirio.br',
      v_prof_ana_id,
      v_ic_id,
      v_batch_id,
      v_ic_type_id,
      'published',
      TRUE,
      DATE '2026-04-01',
      DATE '2027-03-31',
      NOW() - INTERVAL '12 days'
    )
    RETURNING id INTO v_project_2;
  ELSE
    UPDATE projects SET
      title = 'DEMO - Modelos Inteligentes para Catalogos Academicos',
      short_description = 'Pesquisa sobre organizacao, busca e recomendacao de projetos academicos em portais institucionais.',
      full_description = 'Projeto de iniciacao cientifica que investiga formas de estruturar catalogos academicos, melhorar busca textual e apoiar recomendacoes de projetos conforme areas, cursos e unidades institucionais.',
      contact_email = 'ana.martins@demo.unirio.br',
      owner_professor_id = v_prof_ana_id,
      executing_unit_id = v_ic_id,
      source_import_batch_id = v_batch_id,
      project_type_id = v_ic_type_id,
      status = 'published',
      is_active = TRUE,
      starts_at = DATE '2026-04-01',
      ends_at = DATE '2027-03-31',
      published_at = COALESCE(published_at, NOW() - INTERVAL '12 days'),
      updated_at = NOW()
    WHERE id = v_project_2;
  END IF;

  SELECT id INTO v_project_3 FROM projects WHERE process_code = 'DEMO-SIEPA-EXT-002' LIMIT 1;
  IF v_project_3 IS NULL THEN
    INSERT INTO projects (
      process_code, title, short_description, full_description, contact_email,
      owner_professor_id, executing_unit_id, source_import_batch_id, project_type_id,
      status, is_active, starts_at, ends_at, published_at
    )
    VALUES (
      'DEMO-SIEPA-EXT-002',
      'DEMO - Educacao Ambiental em Escolas Publicas',
      'Acoes educativas sobre sustentabilidade, biodiversidade e preservacao ambiental em escolas parceiras.',
      'Projeto de extensao que desenvolve atividades com estudantes da educacao basica, articulando ciencias biologicas, meio ambiente e praticas pedagogicas para promover consciencia ambiental.',
      'bruno.costa@demo.unirio.br',
      v_prof_bruno_id,
      v_ibio_id,
      v_batch_id,
      v_extensao_id,
      'published',
      TRUE,
      DATE '2026-02-15',
      DATE '2026-11-30',
      NOW() - INTERVAL '9 days'
    )
    RETURNING id INTO v_project_3;
  ELSE
    UPDATE projects SET
      title = 'DEMO - Educacao Ambiental em Escolas Publicas',
      short_description = 'Acoes educativas sobre sustentabilidade, biodiversidade e preservacao ambiental em escolas parceiras.',
      full_description = 'Projeto de extensao que desenvolve atividades com estudantes da educacao basica, articulando ciencias biologicas, meio ambiente e praticas pedagogicas para promover consciencia ambiental.',
      contact_email = 'bruno.costa@demo.unirio.br',
      owner_professor_id = v_prof_bruno_id,
      executing_unit_id = v_ibio_id,
      source_import_batch_id = v_batch_id,
      project_type_id = v_extensao_id,
      status = 'published',
      is_active = TRUE,
      starts_at = DATE '2026-02-15',
      ends_at = DATE '2026-11-30',
      published_at = COALESCE(published_at, NOW() - INTERVAL '9 days'),
      updated_at = NOW()
    WHERE id = v_project_3;
  END IF;

  SELECT id INTO v_project_4 FROM projects WHERE process_code = 'DEMO-SIEPA-EXT-003' LIMIT 1;
  IF v_project_4 IS NULL THEN
    INSERT INTO projects (
      process_code, title, short_description, full_description, contact_email,
      owner_professor_id, executing_unit_id, source_import_batch_id, project_type_id,
      status, is_active, starts_at, ends_at, published_at
    )
    VALUES (
      'DEMO-SIEPA-EXT-003',
      'DEMO - Musica, Memoria e Territorio',
      'Atividades culturais e oficinas musicais para valorizacao da memoria local e producao artistica comunitaria.',
      'Projeto de extensao que integra estudantes e comunidade por meio de oficinas, rodas de conversa, apresentacoes e registros culturais ligados a musica, memoria e territorio.',
      'carla.souza@demo.unirio.br',
      v_prof_carla_id,
      v_ia_id,
      v_batch_id,
      v_extensao_id,
      'published',
      TRUE,
      DATE '2026-05-01',
      DATE '2026-10-30',
      NOW() - INTERVAL '7 days'
    )
    RETURNING id INTO v_project_4;
  ELSE
    UPDATE projects SET
      title = 'DEMO - Musica, Memoria e Territorio',
      short_description = 'Atividades culturais e oficinas musicais para valorizacao da memoria local e producao artistica comunitaria.',
      full_description = 'Projeto de extensao que integra estudantes e comunidade por meio de oficinas, rodas de conversa, apresentacoes e registros culturais ligados a musica, memoria e territorio.',
      contact_email = 'carla.souza@demo.unirio.br',
      owner_professor_id = v_prof_carla_id,
      executing_unit_id = v_ia_id,
      source_import_batch_id = v_batch_id,
      project_type_id = v_extensao_id,
      status = 'published',
      is_active = TRUE,
      starts_at = DATE '2026-05-01',
      ends_at = DATE '2026-10-30',
      published_at = COALESCE(published_at, NOW() - INTERVAL '7 days'),
      updated_at = NOW()
    WHERE id = v_project_4;
  END IF;

  SELECT id INTO v_project_5 FROM projects WHERE process_code = 'DEMO-SIEPA-IC-002' LIMIT 1;
  IF v_project_5 IS NULL THEN
    INSERT INTO projects (
      process_code, title, short_description, full_description, contact_email,
      owner_professor_id, executing_unit_id, source_import_batch_id, project_type_id,
      status, is_active, starts_at, ends_at, published_at
    )
    VALUES (
      'DEMO-SIEPA-IC-002',
      'DEMO - Indicadores de Permanencia Estudantil',
      'Estudo exploratorio sobre dados academicos, permanencia estudantil e visualizacao de indicadores.',
      'Projeto de iniciacao cientifica voltado para analise de dados institucionais, producao de indicadores e construcao de visualizacoes que apoiem a compreensao de trajetorias academicas.',
      'carla.souza@demo.unirio.br',
      v_prof_carla_id,
      v_eco_id,
      v_batch_id,
      v_ic_type_id,
      'published',
      TRUE,
      DATE '2026-03-10',
      DATE '2027-02-28',
      NOW() - INTERVAL '4 days'
    )
    RETURNING id INTO v_project_5;
  ELSE
    UPDATE projects SET
      title = 'DEMO - Indicadores de Permanencia Estudantil',
      short_description = 'Estudo exploratorio sobre dados academicos, permanencia estudantil e visualizacao de indicadores.',
      full_description = 'Projeto de iniciacao cientifica voltado para analise de dados institucionais, producao de indicadores e construcao de visualizacoes que apoiem a compreensao de trajetorias academicas.',
      contact_email = 'carla.souza@demo.unirio.br',
      owner_professor_id = v_prof_carla_id,
      executing_unit_id = v_eco_id,
      source_import_batch_id = v_batch_id,
      project_type_id = v_ic_type_id,
      status = 'published',
      is_active = TRUE,
      starts_at = DATE '2026-03-10',
      ends_at = DATE '2027-02-28',
      published_at = COALESCE(published_at, NOW() - INTERVAL '4 days'),
      updated_at = NOW()
    WHERE id = v_project_5;
  END IF;

  SELECT id INTO v_project_6 FROM projects WHERE process_code = 'DEMO-SIEPA-DRAFT-001' LIMIT 1;
  IF v_project_6 IS NULL THEN
    INSERT INTO projects (
      process_code, title, short_description, full_description, contact_email,
      owner_professor_id, executing_unit_id, source_import_batch_id, project_type_id,
      status, is_active, starts_at, ends_at, published_at
    )
    VALUES (
      'DEMO-SIEPA-DRAFT-001',
      'DEMO - Projeto Rascunho para Teste de Area Administrativa',
      'Este projeto fica em draft para testar se a listagem publica ignora rascunhos.',
      'Registro demonstrativo usado para validar regras de visibilidade. Nao deve aparecer na listagem publica de projetos publicados.',
      'ana.martins@demo.unirio.br',
      v_prof_ana_id,
      v_ic_id,
      v_batch_id,
      v_extensao_id,
      'draft',
      TRUE,
      DATE '2026-08-01',
      DATE '2026-12-01',
      NULL
    )
    RETURNING id INTO v_project_6;
  END IF;

  -- Links de áreas
  INSERT INTO project_area_links (project_id, area_id)
  VALUES
    (v_project_1, v_area_tecnologia),
    (v_project_1, v_area_educacao),
    (v_project_2, v_area_tecnologia),
    (v_project_2, v_area_educacao),
    (v_project_3, v_area_meio_ambiente),
    (v_project_3, v_area_educacao),
    (v_project_4, v_area_cultura),
    (v_project_5, v_area_educacao),
    (v_project_5, v_area_tecnologia),
    (v_project_6, v_area_tecnologia)
  ON CONFLICT DO NOTHING;

  -- Links de cursos
  INSERT INTO project_course_links (project_id, course_id)
  VALUES
    (v_project_1, v_curso_si),
    (v_project_1, v_curso_mestrado_info),
    (v_project_2, v_curso_si),
    (v_project_2, v_curso_mestrado_info),
    (v_project_3, v_curso_bio),
    (v_project_3, v_curso_pedagogia),
    (v_project_3, v_curso_enfermagem),
    (v_project_4, v_curso_musica),
    (v_project_4, v_curso_pedagogia),
    (v_project_5, v_curso_pedagogia),
    (v_project_5, v_curso_si),
    (v_project_6, v_curso_si)
  ON CONFLICT DO NOTHING;

  -- Imagens de capa
  INSERT INTO project_images (project_id, image_type, image_url, alt_text, sort_order)
  VALUES
    (v_project_1, 'cover', 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3', 'Pessoas estudando tecnologia em notebooks', 0),
    (v_project_2, 'cover', 'https://images.unsplash.com/photo-1451187580459-43490279c0fa', 'Visualizacao abstrata de tecnologia e dados', 0),
    (v_project_3, 'cover', 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e', 'Trilha em floresta representando meio ambiente', 0),
    (v_project_4, 'cover', 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f', 'Instrumentos musicais em ambiente cultural', 0),
    (v_project_5, 'cover', 'https://images.unsplash.com/photo-1551288049-bebda4e38f71', 'Graficos e indicadores em tela digital', 0),
    (v_project_6, 'cover', 'https://images.unsplash.com/photo-1498050108023-c5249f4df085', 'Codigo em tela de computador', 0)
  ON CONFLICT (project_id) WHERE image_type = 'cover'
  DO UPDATE SET
    image_url = EXCLUDED.image_url,
    alt_text = EXCLUDED.alt_text,
    sort_order = EXCLUDED.sort_order;

  -- Galeria simples
  INSERT INTO project_images (project_id, image_type, image_url, alt_text, sort_order)
  SELECT v_project_1, 'gallery', 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f', 'Grupo em atividade colaborativa', 1
  WHERE NOT EXISTS (
    SELECT 1 FROM project_images WHERE project_id = v_project_1 AND image_type = 'gallery' AND image_url = 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f'
  );

  INSERT INTO project_images (project_id, image_type, image_url, alt_text, sort_order)
  SELECT v_project_3, 'gallery', 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee', 'Paisagem natural em atividade ambiental', 1
  WHERE NOT EXISTS (
    SELECT 1 FROM project_images WHERE project_id = v_project_3 AND image_type = 'gallery' AND image_url = 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee'
  );

  -- Atribuições e vínculos de cursos
  SELECT id INTO v_assignment_id
  FROM project_assignments
  WHERE project_id = v_project_1 AND description = 'Ministrar oficinas introdutorias de HTML, CSS e cidadania digital.'
  LIMIT 1;
  IF v_assignment_id IS NULL THEN
    INSERT INTO project_assignments (project_id, description, sort_order, is_active)
    VALUES (v_project_1, 'Ministrar oficinas introdutorias de HTML, CSS e cidadania digital.', 0, TRUE)
    RETURNING id INTO v_assignment_id;
  END IF;
  INSERT INTO project_assignment_courses (project_assignment_id, course_id)
  VALUES (v_assignment_id, v_curso_si), (v_assignment_id, v_curso_mestrado_info)
  ON CONFLICT DO NOTHING;

  SELECT id INTO v_assignment_id
  FROM project_assignments
  WHERE project_id = v_project_1 AND description = 'Apoiar levantamento de demandas da comunidade e organizacao dos materiais didaticos.'
  LIMIT 1;
  IF v_assignment_id IS NULL THEN
    INSERT INTO project_assignments (project_id, description, sort_order, is_active)
    VALUES (v_project_1, 'Apoiar levantamento de demandas da comunidade e organizacao dos materiais didaticos.', 1, TRUE)
    RETURNING id INTO v_assignment_id;
  END IF;
  INSERT INTO project_assignment_courses (project_assignment_id, course_id)
  VALUES (v_assignment_id, v_curso_si)
  ON CONFLICT DO NOTHING;

  SELECT id INTO v_assignment_id
  FROM project_assignments
  WHERE project_id = v_project_2 AND description = 'Investigar modelos de busca textual e ranking para catalogos de projetos.'
  LIMIT 1;
  IF v_assignment_id IS NULL THEN
    INSERT INTO project_assignments (project_id, description, sort_order, is_active)
    VALUES (v_project_2, 'Investigar modelos de busca textual e ranking para catalogos de projetos.', 0, TRUE)
    RETURNING id INTO v_assignment_id;
  END IF;
  INSERT INTO project_assignment_courses (project_assignment_id, course_id)
  VALUES (v_assignment_id, v_curso_si), (v_assignment_id, v_curso_mestrado_info)
  ON CONFLICT DO NOTHING;

  SELECT id INTO v_assignment_id
  FROM project_assignments
  WHERE project_id = v_project_3 AND description = 'Planejar atividades educativas sobre biodiversidade e sustentabilidade.'
  LIMIT 1;
  IF v_assignment_id IS NULL THEN
    INSERT INTO project_assignments (project_id, description, sort_order, is_active)
    VALUES (v_project_3, 'Planejar atividades educativas sobre biodiversidade e sustentabilidade.', 0, TRUE)
    RETURNING id INTO v_assignment_id;
  END IF;
  INSERT INTO project_assignment_courses (project_assignment_id, course_id)
  VALUES (v_assignment_id, v_curso_bio), (v_assignment_id, v_curso_pedagogia)
  ON CONFLICT DO NOTHING;

  SELECT id INTO v_assignment_id
  FROM project_assignments
  WHERE project_id = v_project_4 AND description = 'Organizar oficinas musicais e registros culturais com participantes da comunidade.'
  LIMIT 1;
  IF v_assignment_id IS NULL THEN
    INSERT INTO project_assignments (project_id, description, sort_order, is_active)
    VALUES (v_project_4, 'Organizar oficinas musicais e registros culturais com participantes da comunidade.', 0, TRUE)
    RETURNING id INTO v_assignment_id;
  END IF;
  INSERT INTO project_assignment_courses (project_assignment_id, course_id)
  VALUES (v_assignment_id, v_curso_musica), (v_assignment_id, v_curso_pedagogia)
  ON CONFLICT DO NOTHING;

  SELECT id INTO v_assignment_id
  FROM project_assignments
  WHERE project_id = v_project_5 AND description = 'Construir painéis de indicadores e validar visualizacoes com usuarios internos.'
  LIMIT 1;
  IF v_assignment_id IS NULL THEN
    INSERT INTO project_assignments (project_id, description, sort_order, is_active)
    VALUES (v_project_5, 'Construir painéis de indicadores e validar visualizacoes com usuarios internos.', 0, TRUE)
    RETURNING id INTO v_assignment_id;
  END IF;
  INSERT INTO project_assignment_courses (project_assignment_id, course_id)
  VALUES (v_assignment_id, v_curso_si), (v_assignment_id, v_curso_pedagogia)
  ON CONFLICT DO NOTHING;

  -- Links de importação
  INSERT INTO project_import_links (project_id, import_batch_id)
  VALUES
    (v_project_1, v_batch_id),
    (v_project_2, v_batch_id),
    (v_project_3, v_batch_id),
    (v_project_4, v_batch_id),
    (v_project_5, v_batch_id),
    (v_project_6, v_batch_id)
  ON CONFLICT DO NOTHING;

  -- Log de auditoria demo
  INSERT INTO project_change_logs (
    project_id,
    changed_by_user_id,
    change_type,
    field_name,
    old_value,
    new_value,
    reason
  )
  SELECT
    v_project_1,
    v_admin_id,
    'import_override',
    'seed_demo',
    NULL,
    jsonb_build_object('status', 'created_or_updated_by_seed'),
    'Carga demonstrativa para visualizacao em ambiente de producao.'
  WHERE NOT EXISTS (
    SELECT 1
    FROM project_change_logs
    WHERE project_id = v_project_1
      AND field_name = 'seed_demo'
      AND reason = 'Carga demonstrativa para visualizacao em ambiente de producao.'
  );
END $$;

COMMIT;

-- Consultas rápidas para validar:
-- SELECT id, process_code, title, status, is_active FROM projects WHERE process_code LIKE 'DEMO-SIEPA-%' ORDER BY id;
-- SELECT p.process_code, p.title, pa.name AS area FROM projects p JOIN project_area_links pal ON pal.project_id = p.id JOIN project_areas pa ON pa.id = pal.area_id WHERE p.process_code LIKE 'DEMO-SIEPA-%' ORDER BY p.process_code, pa.name;
-- SELECT p.process_code, p.title, c.name AS curso FROM projects p JOIN project_course_links pcl ON pcl.project_id = p.id JOIN courses c ON c.id = pcl.course_id WHERE p.process_code LIKE 'DEMO-SIEPA-%' ORDER BY p.process_code, c.name;
