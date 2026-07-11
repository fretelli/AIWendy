"""Add calculation lineage to fundamental dossiers.

Revision ID: 028
Revises: 027
"""
from alembic import op

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in (
        "ALTER TABLE agent_company_dossiers ADD COLUMN IF NOT EXISTS calculation_version VARCHAR(40)",
        "ALTER TABLE agent_company_dossiers ADD COLUMN IF NOT EXISTS financial_as_of VARCHAR(20)",
        "ALTER TABLE agent_company_dossiers ADD COLUMN IF NOT EXISTS calculation_errors JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ALTER TABLE agent_company_dossier_versions ADD COLUMN IF NOT EXISTS calculation_version VARCHAR(40) NOT NULL DEFAULT 'fundamental-v2'",
        "ALTER TABLE agent_company_dossier_versions ADD COLUMN IF NOT EXISTS financial_as_of VARCHAR(20)",
        "ALTER TABLE agent_company_dossier_versions ADD COLUMN IF NOT EXISTS quality JSONB NOT NULL DEFAULT '{}'::jsonb",
        "ALTER TABLE agent_company_dossier_versions ADD COLUMN IF NOT EXISTS calculation_errors JSONB NOT NULL DEFAULT '[]'::jsonb",
    ):
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Migration 028 is not reversible")
