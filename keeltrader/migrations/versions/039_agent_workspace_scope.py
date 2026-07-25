"""Add explicit Agent workspace scope.

Revision ID: 039
Revises: 038
"""
from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE agent_platform_sessions ADD COLUMN workspace_scope VARCHAR(20) NOT NULL DEFAULT 'research'")
    op.execute("ALTER TABLE agent_platform_sessions ADD CONSTRAINT ck_agent_sessions_workspace_scope CHECK (workspace_scope IN ('general','research','content','ops'))")
    op.execute("COMMENT ON COLUMN agent_platform_sessions.workspace_scope IS '会话工作区范围；与ask、research、plan交互方式正交，且不授予主机执行权限'")


def downgrade() -> None:
    raise RuntimeError("Migration 039 is additive and intentionally non-reversible")
