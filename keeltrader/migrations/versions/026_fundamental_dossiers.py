"""Add immutable company dossiers, versions and evidence.

Revision ID: 026
Revises: 025
"""
from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = (
        "CREATE TABLE agent_company_dossiers (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, company_code VARCHAR(20) NOT NULL, company_name VARCHAR(120) NOT NULL, industry VARCHAR(120), current_version INTEGER NOT NULL DEFAULT 0, source_fingerprint VARCHAR(64), status VARCHAR(30) NOT NULL DEFAULT 'pending', stale BOOLEAN NOT NULL DEFAULT true, last_refreshed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(user_id, company_code))",
        "CREATE TABLE agent_company_dossier_versions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), dossier_id UUID NOT NULL REFERENCES agent_company_dossiers(id) ON DELETE CASCADE, version INTEGER NOT NULL, source_fingerprint VARCHAR(64) NOT NULL, snapshot JSONB NOT NULL, diff JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(dossier_id, version))",
        "CREATE TABLE agent_company_evidence (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), dossier_version_id UUID NOT NULL REFERENCES agent_company_dossier_versions(id) ON DELETE CASCADE, source_type VARCHAR(30) NOT NULL, citation JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
        "CREATE INDEX ix_agent_company_dossiers_refresh ON agent_company_dossiers(stale, last_refreshed_at)",
        "CREATE INDEX ix_agent_company_evidence_version ON agent_company_evidence(dossier_version_id)",
    )
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Migration 026 is not reversible")
