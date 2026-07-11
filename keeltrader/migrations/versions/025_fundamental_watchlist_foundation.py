"""Add managed Agent profiles and A-share watchlists.

Revision ID: 025
Revises: 024
"""

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = (
        "ALTER TABLE agent_platform_model_profiles ALTER COLUMN user_id DROP NOT NULL",
        "ALTER TABLE agent_platform_model_profiles ALTER COLUMN api_key_encrypted DROP NOT NULL",
        "ALTER TABLE agent_platform_model_profiles ADD COLUMN IF NOT EXISTS credential_source VARCHAR(20) NOT NULL DEFAULT 'byok'",
        "ALTER TABLE agent_platform_model_profiles ADD COLUMN IF NOT EXISTS managed_slug VARCHAR(80)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_platform_models_managed_slug ON agent_platform_model_profiles(managed_slug) WHERE managed_slug IS NOT NULL",
        "ALTER TABLE agent_platform_definitions ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT false",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_platform_default_definition ON agent_platform_definitions(user_id) WHERE is_default = true AND is_active = true",
        "ALTER TABLE agent_platform_sessions ADD COLUMN IF NOT EXISTS company_code VARCHAR(20)",
        "CREATE INDEX IF NOT EXISTS ix_agent_platform_sessions_company ON agent_platform_sessions(user_id, company_code) WHERE company_code IS NOT NULL",
        "CREATE TABLE IF NOT EXISTS agent_company_watchlist (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, company_code VARCHAR(20) NOT NULL, company_name VARCHAR(120) NOT NULL, industry VARCHAR(120), refresh_enabled BOOLEAN NOT NULL DEFAULT true, added_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id, company_code))",
        "CREATE INDEX IF NOT EXISTS ix_agent_company_watchlist_user ON agent_company_watchlist(user_id, added_at DESC)",
    )
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Migration 025 is not reversible")
