"""Bootstrap core tables and align schema with current models.

Revision ID: 011a
Revises: 010
Create Date: 2026-01-20

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "011a"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    # Ensure required extensions exist for UUIDs and vector embeddings.
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

    # Create missing tables for current models.
    from core.database import Base
    from domain.analysis import models as analysis_models  # noqa: F401
    from domain.coach import models as coach_models  # noqa: F401
    from domain.exchange import models as exchange_models  # noqa: F401
    from domain.intervention import models as intervention_models  # noqa: F401
    from domain.journal import models as journal_models  # noqa: F401
    from domain.knowledge import models as knowledge_models  # noqa: F401
    from domain.notification import models as notification_models  # noqa: F401
    from domain.project import models as project_models  # noqa: F401
    from domain.report import models as report_models  # noqa: F401
    from domain.tenant import models as tenant_models  # noqa: F401
    from domain.user import models as user_models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "username" in user_columns:
            op.execute("ALTER TABLE users ALTER COLUMN username DROP NOT NULL;")

    # Users: add columns introduced after the initial migration.
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(255),
        ADD COLUMN IF NOT EXISTS display_name VARCHAR(100),
        ADD COLUMN IF NOT EXISTS bio TEXT,
        ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC',
        ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en',
        ADD COLUMN IF NOT EXISTS trading_types JSON DEFAULT '[]'::json,
        ADD COLUMN IF NOT EXISTS main_concern TEXT,
        ADD COLUMN IF NOT EXISTS preferred_coach_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS preferred_coach_style VARCHAR(50),
        ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS openai_api_key TEXT,
        ADD COLUMN IF NOT EXISTS anthropic_api_key TEXT,
        ADD COLUMN IF NOT EXISTS api_keys_encrypted JSON DEFAULT '{}'::json,
        ADD COLUMN IF NOT EXISTS notification_preferences JSON DEFAULT '{"email_daily_summary": false, "email_weekly_report": true, "push_notifications": true, "sms_alerts": false}'::json,
        ADD COLUMN IF NOT EXISTS privacy_settings JSON DEFAULT '{"share_analytics": true, "public_profile": false}'::json,
        ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_email_active ON users(email, is_active);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_users_subscription ON users(subscription_tier, subscription_expires_at);"
    )

    # User sessions: ensure indexes exist.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_sessions_access_token ON user_sessions(access_token);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at ON user_sessions(expires_at);"
    )

    # Chat sessions: add project_id and index.
    op.execute(
        """
        ALTER TABLE chat_sessions
        ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_project_created
        ON chat_sessions(user_id, project_id, created_at);
        """
    )

    # Chat messages: ensure attachments flag exists.
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD COLUMN IF NOT EXISTS has_attachments BOOLEAN DEFAULT FALSE;
        """
    )

    # Reports: add project_id and index.
    op.execute(
        """
        ALTER TABLE reports
        ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_reports_user_project_period
        ON reports(user_id, project_id, period_start);
        """
    )

    # Journals: add project_id + deleted_at (for older schemas) and indexes.
    op.execute(
        """
        ALTER TABLE journals
        ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_journals_user_date
        ON journals(user_id, trade_date);
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journals_symbol ON journals(symbol);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_journals_result ON journals(result);"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_journals_user_project_date
        ON journals(user_id, project_id, trade_date);
        """
    )


def downgrade():
    # Non-destructive: leave schema as-is to avoid data loss.
    pass
