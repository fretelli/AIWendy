"""Cross-asset rates, opportunities and private trade planning.

Revision ID: 031
Revises: 030
"""
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE agent_risk_profiles (
        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        account_equity NUMERIC(24,6), currency VARCHAR(12) NOT NULL DEFAULT 'CNY',
        risk_per_trade NUMERIC(12,8) NOT NULL DEFAULT 0.005,
        aggregate_open_risk NUMERIC(12,8) NOT NULL DEFAULT 0.03,
        single_instrument_notional NUMERIC(12,8) NOT NULL DEFAULT 0.20,
        derivative_premium_risk NUMERIC(12,8) NOT NULL DEFAULT 0.005,
        max_leverage NUMERIC(12,8) NOT NULL DEFAULT 1.0,
        sizing_method VARCHAR(40) NOT NULL DEFAULT 'fixed_risk',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("""CREATE TABLE market_opportunities (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), fingerprint VARCHAR(160) NOT NULL UNIQUE,
        playbook_key VARCHAR(80) NOT NULL, title VARCHAR(240) NOT NULL, lifecycle_state VARCHAR(30) NOT NULL,
        hypothesis TEXT NOT NULL, affected_assets JSONB NOT NULL DEFAULT '[]'::jsonb,
        catalysts JSONB NOT NULL DEFAULT '[]'::jsonb, falsifiers JSONB NOT NULL DEFAULT '[]'::jsonb,
        source_dates JSONB NOT NULL DEFAULT '{}'::jsonb, first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("""CREATE TABLE market_opportunity_evidence (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), opportunity_id UUID NOT NULL REFERENCES market_opportunities(id) ON DELETE CASCADE,
        stance VARCHAR(20) NOT NULL, fact TEXT NOT NULL, source VARCHAR(240) NOT NULL,
        source_date VARCHAR(32), source_ref JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX ix_market_opportunity_evidence ON market_opportunity_evidence(opportunity_id, stance)")
    op.execute("""CREATE TABLE agent_opportunity_follows (
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        opportunity_id UUID NOT NULL REFERENCES market_opportunities(id) ON DELETE CASCADE,
        state VARCHAR(20) NOT NULL DEFAULT 'following', notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(user_id, opportunity_id))""")
    op.execute("""CREATE TABLE agent_trade_plan_drafts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        opportunity_id UUID NOT NULL REFERENCES market_opportunities(id) ON DELETE CASCADE,
        status VARCHAR(30) NOT NULL, unavailable_reason TEXT, direction VARCHAR(20), instrument VARCHAR(80),
        entry_trigger TEXT, entry_price NUMERIC(24,8), stop_price NUMERIC(24,8), target_price NUMERIC(24,8),
        horizon VARCHAR(80), quantity NUMERIC(24,8), max_loss NUMERIC(24,8), notional NUMERIC(24,8),
        checklist JSONB NOT NULL DEFAULT '[]'::jsonb, assumptions JSONB NOT NULL DEFAULT '{}'::jsonb,
        human_confirmation_required BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX ix_agent_trade_plans_user ON agent_trade_plan_drafts(user_id, updated_at DESC)")


def downgrade() -> None:
    raise RuntimeError("Migration 031 is additive and intentionally non-reversible")
