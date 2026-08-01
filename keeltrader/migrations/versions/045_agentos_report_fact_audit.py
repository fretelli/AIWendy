"""Audit immutable bilingual report facts and downloads.

Revision ID: 045
Revises: 044
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("research_document_versions", sa.Column("fact_snapshot_sha256", sa.String(64), nullable=True,
                  comment="中英文版本共享的不可变事实快照哈希"))
    op.create_table("research_document_downloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"),
                  comment="下载审计记录唯一标识"),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_document_versions.id", ondelete="CASCADE"), nullable=False,
                  comment="被下载的不可变报告版本"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
                  comment="执行下载的用户"),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
                  comment="下载发生时间"),
        comment="双语报告版本下载审计")
    op.create_index("ix_research_document_download_version", "research_document_downloads", ["version_id", "downloaded_at"])


def downgrade() -> None:
    op.drop_table("research_document_downloads")
    op.drop_column("research_document_versions", "fact_snapshot_sha256")
