"""Add user-scoped shareholder watchlists and event inbox.

Revision ID: 029
Revises: 028
"""

from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in (
        "CREATE TABLE agent_holder_watchlist (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, holder_name VARCHAR(500) NOT NULL, normalized_name VARCHAR(500) NOT NULL, holder_type VARCHAR(80) NOT NULL DEFAULT '未知', aliases JSONB NOT NULL DEFAULT '[]'::jsonb, enabled BOOLEAN NOT NULL DEFAULT true, last_scanned_at TIMESTAMPTZ, last_source_watermark VARCHAR(80), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())",
        "CREATE UNIQUE INDEX uq_agent_holder_watchlist_user_match ON agent_holder_watchlist(user_id, normalized_name, holder_type)",
        "CREATE INDEX ix_agent_holder_watchlist_user ON agent_holder_watchlist(user_id, created_at DESC)",
        "CREATE TABLE agent_holder_events (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, watch_id UUID NOT NULL REFERENCES agent_holder_watchlist(id) ON DELETE CASCADE, event_key VARCHAR(64) NOT NULL, ts_code VARCHAR(20) NOT NULL, company_name VARCHAR(120), holder_name VARCHAR(500) NOT NULL, holder_type VARCHAR(80) NOT NULL DEFAULT '未知', event_type VARCHAR(40) NOT NULL, end_date VARCHAR(8) NOT NULL, ann_date VARCHAR(8), previous_end_date VARCHAR(8), values JSONB NOT NULL DEFAULT '{}'::jsonb, read_at TIMESTAMPTZ, detected_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())",
        "CREATE UNIQUE INDEX uq_agent_holder_event_period ON agent_holder_events(watch_id, ts_code, end_date)",
        "CREATE UNIQUE INDEX uq_agent_holder_event_key ON agent_holder_events(event_key)",
        "CREATE INDEX ix_agent_holder_events_user_unread ON agent_holder_events(user_id, read_at, detected_at DESC)",
        "CREATE INDEX ix_agent_holder_events_watch ON agent_holder_events(watch_id, end_date DESC)",
    ):
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Migration 029 is not reversible")
