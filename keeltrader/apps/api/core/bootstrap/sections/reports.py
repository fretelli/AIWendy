from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_reports_schema(conn: AsyncConnection) -> None:
    # Reports (periodic reports)
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE reporttype AS ENUM ('daily', 'weekly', 'monthly', 'quarterly', 'yearly');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS analysis_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                report_type reporttype NOT NULL,
                period_start TIMESTAMPTZ NOT NULL,
                period_end TIMESTAMPTZ NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                breakeven_trades INTEGER DEFAULT 0,
                win_rate FLOAT,
                profit_factor FLOAT,
                sharpe_ratio FLOAT,
                max_drawdown FLOAT,
                total_pnl FLOAT,
                avg_win FLOAT,
                avg_loss FLOAT,
                best_trade FLOAT,
                worst_trade FLOAT,
                avg_emotion_score FLOAT,
                avg_confidence_score FLOAT,
                avg_stress_score FLOAT,
                rule_violation_rate FLOAT,
                detected_patterns JSON DEFAULT '[]'::json,
                pattern_frequencies JSON DEFAULT '{}'::json,
                pattern_insights JSON DEFAULT '{}'::json,
                ai_summary TEXT,
                ai_recommendations JSON DEFAULT '[]'::json,
                ai_strengths JSON DEFAULT '[]'::json,
                ai_weaknesses JSON DEFAULT '[]'::json,
                ai_action_items JSON DEFAULT '[]'::json,
                key_insights JSON DEFAULT '[]'::json,
                coaching_notes TEXT,
                generated_at TIMESTAMPTZ DEFAULT NOW(),
                viewed_at TIMESTAMPTZ
            );
            """
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_analysis_reports_user_type ON analysis_reports(user_id, report_type);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_analysis_reports_period ON analysis_reports(period_start, period_end);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                metric_date TIMESTAMPTZ NOT NULL,
                daily_pnl FLOAT,
                daily_trades INTEGER DEFAULT 0,
                daily_win_rate FLOAT,
                cumulative_pnl FLOAT,
                cumulative_trades INTEGER DEFAULT 0,
                account_balance FLOAT,
                daily_var FLOAT,
                daily_max_drawdown FLOAT,
                avg_emotion FLOAT,
                avg_confidence FLOAT,
                rule_violations INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_performance_metrics_user_date ON performance_metrics(user_id, metric_date);"
        )
    )

    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE reportstatus AS ENUM ('pending', 'generating', 'completed', 'failed', 'sent');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

                report_type reporttype NOT NULL,
                title VARCHAR(200) NOT NULL,
                subtitle VARCHAR(500),

                period_start DATE NOT NULL,
                period_end DATE NOT NULL,

                summary TEXT,
                content JSONB,

                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate FLOAT,

                total_pnl FLOAT DEFAULT 0.0,
                avg_pnl FLOAT,
                max_profit FLOAT,
                max_loss FLOAT,

                avg_mood_before FLOAT,
                avg_mood_after FLOAT,
                mood_improvement FLOAT,

                top_mistakes JSONB DEFAULT '[]'::jsonb,
                top_successes JSONB DEFAULT '[]'::jsonb,
                improvements JSONB DEFAULT '[]'::jsonb,

                ai_analysis TEXT,
                ai_recommendations JSONB DEFAULT '[]'::jsonb,
                key_insights JSONB DEFAULT '[]'::jsonb,
                action_items JSONB DEFAULT '[]'::jsonb,

                coach_notes JSONB DEFAULT '{}'::jsonb,
                primary_coach_id VARCHAR(50),

                is_public BOOLEAN DEFAULT FALSE,
                is_archived BOOLEAN DEFAULT FALSE,

                status reportstatus DEFAULT 'pending',
                generation_time FLOAT,
                error_message TEXT,

                email_sent BOOLEAN DEFAULT FALSE,
                email_sent_at TIMESTAMPTZ,

                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    # Upgrades for existing databases
    await conn.execute(
        text(
            """
            ALTER TABLE reports
            ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_reports_user_type ON reports(user_id, report_type);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_reports_user_period ON reports(user_id, period_start, period_end);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_reports_user_project_period ON reports(user_id, project_id, period_start);"
        )
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_reports_status ON reports(status);")
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS report_schedules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,

                daily_enabled BOOLEAN DEFAULT TRUE,
                daily_time VARCHAR(5) DEFAULT '21:00',

                weekly_enabled BOOLEAN DEFAULT TRUE,
                weekly_day INTEGER DEFAULT 0,
                weekly_time VARCHAR(5) DEFAULT '18:00',

                monthly_enabled BOOLEAN DEFAULT TRUE,
                monthly_day INTEGER DEFAULT 1,
                monthly_time VARCHAR(5) DEFAULT '18:00',

                email_notification BOOLEAN DEFAULT TRUE,
                in_app_notification BOOLEAN DEFAULT TRUE,

                include_charts BOOLEAN DEFAULT TRUE,
                include_ai_analysis BOOLEAN DEFAULT TRUE,
                include_coach_feedback BOOLEAN DEFAULT TRUE,

                language VARCHAR(5) DEFAULT 'zh',
                timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
                is_active BOOLEAN DEFAULT TRUE,

                last_daily_generated TIMESTAMPTZ,
                last_weekly_generated TIMESTAMPTZ,
                last_monthly_generated TIMESTAMPTZ,

                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_report_schedules_user ON report_schedules(user_id);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS report_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                report_type reporttype NOT NULL,

                sections JSONB NOT NULL,
                metrics JSONB NOT NULL,
                charts JSONB NOT NULL,

                summary_prompt TEXT,
                analysis_prompt TEXT,
                recommendation_prompt TEXT,

                theme VARCHAR(50) DEFAULT 'default',
                color_scheme JSONB,

                is_default BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                is_premium BOOLEAN DEFAULT FALSE,

                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_report_templates_type ON report_templates(report_type, is_active);"
        )
    )
