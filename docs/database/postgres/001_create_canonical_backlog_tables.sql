-- Canonical backlog persistence schema
-- Story: design-canonical-backlog-persistence
-- Status: Implemented baseline; applied to the sandbox environment.

BEGIN;

SET search_path TO johnny_johnny;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name text NOT NULL,
    primary_email text NULL,
    preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_primary_email
    ON users (lower(primary_email))
    WHERE primary_email IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS providers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    key text NOT NULL,
    display_name text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz NULL,
    CONSTRAINT ux_providers_key UNIQUE (key)
);

CREATE TABLE IF NOT EXISTS provider_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    provider_id uuid NOT NULL REFERENCES providers(id),
    external_id text NULL,
    username text NOT NULL,
    display_name text NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_provider_accounts_username
    ON provider_accounts (provider_id, lower(username))
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_provider_accounts_external_id
    ON provider_accounts (provider_id, external_id)
    WHERE external_id IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS provider_projects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_account_id uuid NOT NULL REFERENCES provider_accounts(id),
    external_id text NULL,
    external_number integer NULL,
    title text NOT NULL,
    url text NULL,
    description text NULL,
    provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_provider_projects_title
    ON provider_projects (provider_account_id, lower(title))
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_provider_projects_external_id
    ON provider_projects (provider_account_id, external_id)
    WHERE external_id IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS backlog_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_project_id uuid NOT NULL REFERENCES provider_projects(id) ON DELETE CASCADE,
    parent_item_id uuid NULL REFERENCES backlog_items(id) ON DELETE SET NULL,
    canonical_id text NOT NULL,
    item_type text NOT NULL,
    title text NOT NULL,
    description text NOT NULL DEFAULT '',
    repository text NOT NULL,
    status text NOT NULL,
    issue_state text NOT NULL,
    item_order integer NOT NULL,
    priority text NULL,
    milestone text NULL,
    external_id text NULL,
    external_database_id bigint NULL,
    external_number integer NULL,
    external_url text NULL,
    external_project_item_id text NULL,
    provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id uuid NULL REFERENCES users(id),
    updated_by_user_id uuid NULL REFERENCES users(id),
    closed_by_user_id uuid NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    closed_at timestamptz NULL,
    archived_at timestamptz NULL,
    deleted_at timestamptz NULL,
    CONSTRAINT ck_backlog_items_item_type CHECK (item_type IN ('epic', 'issue')),
    CONSTRAINT ck_backlog_items_parent_not_self CHECK (parent_item_id IS NULL OR parent_item_id <> id),
    CONSTRAINT ux_backlog_items_canonical_id UNIQUE (provider_project_id, canonical_id)
);

CREATE INDEX IF NOT EXISTS ix_backlog_items_project_parent_order
    ON backlog_items (provider_project_id, parent_item_id, item_order, canonical_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_backlog_items_status
    ON backlog_items (provider_project_id, status)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_backlog_items_issue_state
    ON backlog_items (provider_project_id, issue_state)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_backlog_items_repository
    ON backlog_items (provider_project_id, repository)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS backlog_item_acceptance_criteria (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    backlog_item_id uuid NOT NULL REFERENCES backlog_items(id) ON DELETE CASCADE,
    position integer NOT NULL,
    body text NOT NULL,
    checked boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz NULL,
    CONSTRAINT ux_backlog_item_acceptance_position UNIQUE (backlog_item_id, position)
);

CREATE TABLE IF NOT EXISTS backlog_item_comments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    backlog_item_id uuid NOT NULL REFERENCES backlog_items(id) ON DELETE CASCADE,
    canonical_comment_id text NULL,
    position integer NOT NULL,
    body text NOT NULL,
    source text NOT NULL DEFAULT 'johnny-johnny',
    provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id uuid NULL REFERENCES users(id),
    created_at timestamptz NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz NULL,
    CONSTRAINT ux_backlog_item_comments_position UNIQUE (backlog_item_id, position)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_backlog_item_comments_canonical_comment_id
    ON backlog_item_comments (backlog_item_id, canonical_comment_id)
    WHERE canonical_comment_id IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS backlog_item_labels (
    backlog_item_id uuid NOT NULL REFERENCES backlog_items(id) ON DELETE CASCADE,
    label text NOT NULL,
    PRIMARY KEY (backlog_item_id, label)
);

CREATE TABLE IF NOT EXISTS backlog_item_assignees (
    backlog_item_id uuid NOT NULL REFERENCES backlog_items(id) ON DELETE CASCADE,
    assignee text NOT NULL,
    PRIMARY KEY (backlog_item_id, assignee)
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_providers_updated_at ON providers;
CREATE TRIGGER trg_providers_updated_at
BEFORE UPDATE ON providers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_provider_accounts_updated_at ON provider_accounts;
CREATE TRIGGER trg_provider_accounts_updated_at
BEFORE UPDATE ON provider_accounts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_provider_projects_updated_at ON provider_projects;
CREATE TRIGGER trg_provider_projects_updated_at
BEFORE UPDATE ON provider_projects
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_backlog_items_updated_at ON backlog_items;
CREATE TRIGGER trg_backlog_items_updated_at
BEFORE UPDATE ON backlog_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_acceptance_criteria_updated_at ON backlog_item_acceptance_criteria;
CREATE TRIGGER trg_acceptance_criteria_updated_at
BEFORE UPDATE ON backlog_item_acceptance_criteria
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
