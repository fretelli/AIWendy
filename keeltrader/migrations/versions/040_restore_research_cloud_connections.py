"""Restore the optional user-owned Research Cloud connection table.

Revision ID: 040
Revises: 039
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_cloud_connections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="连接记录主键",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="所属用户标识；连接严格按用户隔离",
        ),
        sa.Column("base_url", sa.String(500), nullable=False, comment="管理员允许的 Research Cloud HTTPS 基础地址"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending", comment="设备授权连接状态"),
        sa.Column("client_id", sa.String(100), comment="远端设备授权客户端标识；不属于认证秘密"),
        sa.Column("api_key_encrypted", sa.Text(), comment="用户 Research Cloud API key 密文；禁止记录、返回或传入模型上下文"),
        sa.Column("key_prefix", sa.String(64), comment="供用户辨识密钥的非秘密前缀"),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="远端授予的最小权限集合"),
        sa.Column("plan_code", sa.String(100), comment="远端返回的计划标识；不作为本地授权依据"),
        sa.Column("pending_device_code_encrypted", sa.Text(), comment="待完成设备授权码密文；属于短期认证秘密"),
        sa.Column("user_code", sa.String(32), comment="展示给用户的短期设备授权代码"),
        sa.Column("verification_uri", sa.String(500), comment="用户完成设备授权的 HTTPS 地址"),
        sa.Column("device_expires_at", sa.DateTime(timezone=True), comment="待完成设备授权的过期时间"),
        sa.Column("cloud_auto_context", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否允许把最小远端检索结果加入研究上下文"),
        sa.Column("connected_at", sa.DateTime(timezone=True), comment="最近一次连接成功时间"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), comment="最近一次连接状态检查时间"),
        sa.Column("last_error", sa.Text(), comment="脱敏后的最近连接错误摘要"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="记录创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="记录最后更新时间"),
        sa.UniqueConstraint("user_id", name="uq_research_cloud_connections_user_id"),
        comment="用户可选的 Research Cloud 设备授权连接；仅传递明确的检索参数和报告标识",
    )
    op.create_index(
        "ix_research_cloud_connections_user_id",
        "research_cloud_connections",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_cloud_connections_user_id",
        table_name="research_cloud_connections",
    )
    op.drop_table("research_cloud_connections")
