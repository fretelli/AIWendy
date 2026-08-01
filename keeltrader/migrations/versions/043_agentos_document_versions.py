"""Add versioned bilingual AgentOS research documents.

Revision ID: 043
Revises: 042
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def c(name, type_, *args, comment: str, **kwargs):
    return sa.Column(name, type_, *args, comment=comment, **kwargs)


def upgrade() -> None:
    op.create_table(
        "research_documents",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="研究文档主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("title", sa.String(240), nullable=False, comment="文档标题"),
        c("document_type", sa.String(40), nullable=False, server_default="research_note", comment="文档类型"),
        c("current_version", sa.Integer(), nullable=False, server_default="0", comment="当前双语版本号"),
        c("status", sa.String(30), nullable=False, server_default="draft", comment="文档状态"),
        c("agent_artifact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_platform_artifacts.id", ondelete="SET NULL"), comment="来源 Agent 产物"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        c("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="更新时间"),
        comment="用户拥有的版本化研究笔记和报告",
    )
    op.create_index("ix_research_documents_user", "research_documents", ["user_id", "status", "updated_at"])
    op.create_table(
        "research_document_versions",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="文档语言版本主键"),
        c("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_documents.id", ondelete="CASCADE"), nullable=False, comment="所属文档"),
        c("version", sa.Integer(), nullable=False, comment="不可变内容版本"),
        c("locale", sa.String(12), nullable=False, comment="zh-CN 或 en-US"),
        c("template_version", sa.String(40), nullable=False, comment="渲染模板版本"),
        c("markdown_body", sa.Text(), nullable=False, comment="可复用研究笔记正文"),
        c("structured_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="结构化章节和指标"),
        c("source_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="生成时使用的事实和引用快照"),
        c("storage_path", sa.String(500), comment="PDF 存储路径"),
        c("content_sha256", sa.String(64), comment="PDF 内容校验和"),
        c("mime_type", sa.String(120), nullable=False, server_default="application/pdf", comment="文件类型"),
        c("size_bytes", sa.Integer(), comment="PDF 字节数"),
        c("status", sa.String(30), nullable=False, server_default="pending", comment="生成状态"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="同一事实快照生成的中英文研究文档版本和 PDF 元数据",
    )
    op.create_index("uq_research_document_version_locale", "research_document_versions", ["document_id", "version", "locale"], unique=True)
    op.create_index("ix_research_document_versions_document", "research_document_versions", ["document_id", "version"])


def downgrade() -> None:
    op.drop_table("research_document_versions")
    op.drop_table("research_documents")
