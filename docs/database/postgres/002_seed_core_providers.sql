-- Seed core providers
-- Status: Draft; do not run until reviewed.

BEGIN;

SET search_path TO johnny_johnny;

INSERT INTO providers (key, display_name, enabled, metadata)
VALUES
    ('github', 'GitHub', true, '{}'::jsonb),
    ('jira', 'Jira', false, '{}'::jsonb),
    ('linear', 'Linear', false, '{}'::jsonb),
    ('gitlab', 'GitLab', false, '{}'::jsonb),
    ('local', 'Local', false, '{}'::jsonb)
ON CONFLICT (key) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    enabled = EXCLUDED.enabled,
    updated_at = now();

COMMIT;
