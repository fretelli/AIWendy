"""Durable research-only Agent Platform.

Revision ID: 020
Revises: 019
"""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


TABLES = [
    "agent_platform_usage_ledger", "agent_platform_schedules", "agent_platform_tool_grants",
    "agent_platform_mcp_servers", "agent_platform_memory_versions", "agent_platform_memories",
    "agent_platform_artifacts", "agent_platform_approvals", "agent_platform_run_events",
    "agent_platform_run_steps", "agent_platform_runs", "agent_platform_messages",
    "agent_platform_sessions", "agent_platform_definitions", "agent_platform_model_profiles",
]


def upgrade():
    op.execute("""
    CREATE TABLE agent_platform_model_profiles (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name VARCHAR(120) NOT NULL, provider VARCHAR(30) NOT NULL, base_url VARCHAR(500),
      model VARCHAR(160) NOT NULL, api_key_encrypted TEXT NOT NULL, key_prefix VARCHAR(32),
      context_window INTEGER NOT NULL, max_output_tokens INTEGER NOT NULL,
      input_cost_per_million DOUBLE PRECISION NOT NULL, output_cost_per_million DOUBLE PRECISION NOT NULL,
      is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_models_user ON agent_platform_model_profiles(user_id, created_at);

    CREATE TABLE agent_platform_definitions (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name VARCHAR(120) NOT NULL, description TEXT, system_prompt TEXT NOT NULL,
      role VARCHAR(50) NOT NULL DEFAULT 'custom', model_profile_id UUID REFERENCES agent_platform_model_profiles(id),
      tool_names JSONB NOT NULL DEFAULT '[]', memory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
      max_steps INTEGER NOT NULL DEFAULT 12, max_parallel INTEGER NOT NULL DEFAULT 3,
      task_token_budget INTEGER NOT NULL DEFAULT 50000, task_cost_budget_usd DOUBLE PRECISION NOT NULL DEFAULT 5,
      is_template BOOLEAN NOT NULL DEFAULT FALSE, is_active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_definitions_user ON agent_platform_definitions(user_id, created_at);

    CREATE TABLE agent_platform_sessions (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      agent_definition_id UUID REFERENCES agent_platform_definitions(id), title VARCHAR(200) NOT NULL,
      status VARCHAR(30) NOT NULL DEFAULT 'active', summary TEXT, context_tokens INTEGER NOT NULL DEFAULT 0,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_sessions_user ON agent_platform_sessions(user_id, updated_at);

    CREATE TABLE agent_platform_messages (
      id UUID PRIMARY KEY, session_id UUID NOT NULL REFERENCES agent_platform_sessions(id) ON DELETE CASCADE,
      role VARCHAR(20) NOT NULL, content TEXT NOT NULL, metadata_json JSONB, token_count INTEGER,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_messages_session ON agent_platform_messages(session_id, created_at);

    CREATE TABLE agent_platform_runs (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      session_id UUID NOT NULL REFERENCES agent_platform_sessions(id) ON DELETE CASCADE,
      agent_definition_id UUID REFERENCES agent_platform_definitions(id), prompt TEXT NOT NULL,
      status VARCHAR(30) NOT NULL DEFAULT 'queued', plan JSONB NOT NULL DEFAULT '[]', checkpoint JSONB NOT NULL DEFAULT '{}',
      current_step INTEGER NOT NULL DEFAULT 0, token_budget INTEGER NOT NULL DEFAULT 50000,
      cost_budget_usd DOUBLE PRECISION NOT NULL DEFAULT 5, tokens_used INTEGER NOT NULL DEFAULT 0,
      cost_used_usd DOUBLE PRECISION NOT NULL DEFAULT 0, lease_owner VARCHAR(100), lease_expires_at TIMESTAMPTZ,
      error TEXT, started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_runs_user ON agent_platform_runs(user_id, created_at);
    CREATE INDEX ix_agent_platform_runs_status ON agent_platform_runs(status, created_at);

    CREATE TABLE agent_platform_run_steps (
      id UUID PRIMARY KEY, run_id UUID NOT NULL REFERENCES agent_platform_runs(id) ON DELETE CASCADE,
      sequence INTEGER NOT NULL, agent_role VARCHAR(50) NOT NULL, tool_name VARCHAR(120),
      status VARCHAR(30) NOT NULL DEFAULT 'pending', input_json JSONB NOT NULL DEFAULT '{}', output_json JSONB,
      error TEXT, attempts INTEGER NOT NULL DEFAULT 0, idempotency_key VARCHAR(160) NOT NULL UNIQUE,
      started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_steps_run ON agent_platform_run_steps(run_id, sequence);

    CREATE TABLE agent_platform_run_events (
      id BIGSERIAL PRIMARY KEY, run_id UUID NOT NULL REFERENCES agent_platform_runs(id) ON DELETE CASCADE,
      event_type VARCHAR(60) NOT NULL, payload JSONB NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_events_run ON agent_platform_run_events(run_id, id);

    CREATE TABLE agent_platform_approvals (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      run_id UUID NOT NULL REFERENCES agent_platform_runs(id) ON DELETE CASCADE,
      step_id UUID NOT NULL REFERENCES agent_platform_run_steps(id) ON DELETE CASCADE,
      kind VARCHAR(40) NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'pending', preview JSONB NOT NULL DEFAULT '{}',
      decision_scope VARCHAR(30), reason TEXT, resolved_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_approvals_user ON agent_platform_approvals(user_id, status, created_at);

    CREATE TABLE agent_platform_artifacts (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      run_id UUID NOT NULL REFERENCES agent_platform_runs(id) ON DELETE CASCADE,
      artifact_type VARCHAR(50) NOT NULL, title VARCHAR(240) NOT NULL, content JSONB NOT NULL DEFAULT '{}',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_artifacts_user ON agent_platform_artifacts(user_id, created_at);

    CREATE TABLE agent_platform_memories (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      agent_definition_id UUID REFERENCES agent_platform_definitions(id), key VARCHAR(200) NOT NULL,
      value JSONB NOT NULL, evidence JSONB NOT NULL DEFAULT '[]', confidence DOUBLE PRECISION NOT NULL DEFAULT .5,
      version INTEGER NOT NULL DEFAULT 1, is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_memories_user ON agent_platform_memories(user_id, is_deleted, updated_at);

    CREATE TABLE agent_platform_memory_versions (
      id UUID PRIMARY KEY, memory_id UUID NOT NULL REFERENCES agent_platform_memories(id) ON DELETE CASCADE,
      version INTEGER NOT NULL, value JSONB NOT NULL, evidence JSONB NOT NULL DEFAULT '[]',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(memory_id, version)
    );

    CREATE TABLE agent_platform_mcp_servers (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name VARCHAR(120) NOT NULL, url VARCHAR(500) NOT NULL, auth_encrypted TEXT, auth_prefix VARCHAR(32),
      status VARCHAR(30) NOT NULL DEFAULT 'pending', tools_snapshot JSONB NOT NULL DEFAULT '[]', schema_digest VARCHAR(64),
      allow_private_network BOOLEAN NOT NULL DEFAULT FALSE, last_checked_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_mcp_user ON agent_platform_mcp_servers(user_id, created_at);

    CREATE TABLE agent_platform_tool_grants (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      agent_definition_id UUID REFERENCES agent_platform_definitions(id),
      mcp_server_id UUID NOT NULL REFERENCES agent_platform_mcp_servers(id) ON DELETE CASCADE,
      tool_name VARCHAR(160) NOT NULL, scope VARCHAR(30) NOT NULL DEFAULT 'always', schema_digest VARCHAR(64) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE UNIQUE INDEX ix_agent_platform_grants_unique ON agent_platform_tool_grants
      (user_id, mcp_server_id, tool_name, COALESCE(agent_definition_id, '00000000-0000-0000-0000-000000000000'::uuid));

    CREATE TABLE agent_platform_schedules (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      agent_definition_id UUID NOT NULL REFERENCES agent_platform_definitions(id), name VARCHAR(160) NOT NULL,
      prompt TEXT NOT NULL, cron VARCHAR(80) NOT NULL, timezone VARCHAR(80) NOT NULL DEFAULT 'Asia/Shanghai',
      enabled BOOLEAN NOT NULL DEFAULT TRUE, next_run_at TIMESTAMPTZ, last_run_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_schedules_due ON agent_platform_schedules(enabled, next_run_at);

    CREATE TABLE agent_platform_usage_ledger (
      id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      run_id UUID REFERENCES agent_platform_runs(id) ON DELETE SET NULL,
      model_profile_id UUID REFERENCES agent_platform_model_profiles(id) ON DELETE SET NULL,
      input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0,
      cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX ix_agent_platform_usage_user ON agent_platform_usage_ledger(user_id, created_at);
    """)


def downgrade():
    for table in TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
