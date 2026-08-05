"""Create user-owned uploaded file metadata.

Revision ID: 046
Revises: 045
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), comment="上传文件元数据唯一标识"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
                  comment="拥有该文件的用户"),
        sa.Column("file_name", sa.String(255), nullable=False, comment="用户上传时的原始文件名"),
        sa.Column("file_size", sa.Integer(), nullable=False, comment="文件字节数"),
        sa.Column("mime_type", sa.String(100), nullable=False, comment="上传时验证后的 MIME 类型"),
        sa.Column("file_category", sa.String(50), nullable=False, comment="图片、文档或音频等受支持分类"),
        sa.Column("storage_path", sa.Text(), nullable=False, unique=True, comment="对象存储中的唯一受管路径"),
        sa.Column("thumbnail_base64", sa.Text(), nullable=True, comment="可选的小尺寸 JPEG 缩略图 Base64"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), comment="文件元数据创建时间"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间；为空表示可用"),
        comment="AgentOS 用户上传文件的受管元数据",
    )
    op.create_index("ix_uploaded_files_user_created", "uploaded_files", ["user_id", "created_at"])
    op.create_index("ix_uploaded_files_storage_path", "uploaded_files", ["storage_path"])


def downgrade() -> None:
    op.drop_index("ix_uploaded_files_storage_path", table_name="uploaded_files")
    op.drop_index("ix_uploaded_files_user_created", table_name="uploaded_files")
    op.drop_table("uploaded_files")
