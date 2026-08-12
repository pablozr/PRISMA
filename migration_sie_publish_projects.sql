BEGIN;

UPDATE projects
SET publication_status = 'published',
    is_visible = TRUE,
    published_at = COALESCE(published_at, NOW()),
    updated_at = NOW()
WHERE sie_project_id IS NOT NULL;

COMMIT;
