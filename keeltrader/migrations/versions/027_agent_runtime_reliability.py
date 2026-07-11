"""Add durable Agent runtime jobs, leases, and failure state.

Revision ID: 027
Revises: 026
"""
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = (
        "ALTER TABLE agent_platform_runs ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ",
        "ALTER TABLE agent_platform_runs ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ",
        "ALTER TABLE agent_platform_runs ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE agent_platform_runs ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 3",
        "ALTER TABLE agent_platform_runs ADD COLUMN IF NOT EXISTS generation INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE agent_platform_runs ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(120)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_platform_run_idempotency ON agent_platform_runs(user_id, idempotency_key) WHERE idempotency_key IS NOT NULL",
        "ALTER TABLE agent_company_dossiers ADD COLUMN IF NOT EXISTS last_error TEXT",
        "ALTER TABLE agent_company_dossiers ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ",
        "CREATE TABLE IF NOT EXISTS agent_background_jobs (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, kind VARCHAR(40) NOT NULL, entity_key VARCHAR(240) NOT NULL, payload JSONB NOT NULL DEFAULT '{}'::jsonb, status VARCHAR(30) NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3, available_at TIMESTAMPTZ NOT NULL DEFAULT now(), lease_owner VARCHAR(120), lease_expires_at TIMESTAMPTZ, last_error TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), finished_at TIMESTAMPTZ)",
        "CREATE INDEX IF NOT EXISTS ix_agent_background_jobs_claim ON agent_background_jobs(status, available_at, lease_expires_at)",
        "CREATE INDEX IF NOT EXISTS ix_agent_background_jobs_entity ON agent_background_jobs(kind, entity_key)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_background_jobs_active ON agent_background_jobs(kind, entity_key) WHERE status IN ('queued','running','retry')",
        "INSERT INTO agent_background_jobs (user_id, kind, entity_key, payload) SELECT user_id, 'dossier_refresh', user_id::text || ':' || company_code, jsonb_build_object('company_code', company_code, 'force', false) FROM agent_company_watchlist WHERE refresh_enabled = true ON CONFLICT DO NOTHING",
    )
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Migration 027 is not reversible")
