"""Retire the Today inbox and Thesis logbook, including stored data.

Revision ID: 037
Revises: 036
"""
from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The product feature is intentionally retired. These drops delete all
    # stored thesis versions, evidence, inbox events, and allocation links.
    op.execute("DROP TABLE IF EXISTS allocation_policy_thesis_links CASCADE")
    op.execute("DROP TABLE IF EXISTS research_thesis_evidence_links CASCADE")
    op.execute("DROP TABLE IF EXISTS research_thesis_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS research_events CASCADE")
    op.execute("DROP TABLE IF EXISTS research_theses CASCADE")


def downgrade() -> None:
    raise RuntimeError(
        "Revision 037 permanently deletes the retired Today and Thesis data and cannot be downgraded."
    )
