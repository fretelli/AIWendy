from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_roundtable_schema(conn: AsyncConnection) -> None:
    # Roundtable (multi-coach discussions)
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS coach_presets (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                icon VARCHAR(50),
                coach_ids JSON NOT NULL,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    await conn.execute(
        text(
            """
            INSERT INTO coach_presets (id, name, description, coach_ids, icon, sort_order, is_active)
            VALUES
                ('all_stars', 'All Stars', 'All coaches participate', '["wendy","marcus","sophia","alex","socrates"]'::json, 'stars', 1, TRUE),
                ('rational', 'Rational', 'Data + discipline', '["sophia","marcus"]'::json, 'brain', 2, TRUE),
                ('emotional', 'Emotional', 'Empathy + motivation', '["wendy","alex"]'::json, 'heart', 3, TRUE),
                ('debate', 'Debate', 'Different viewpoints', '["wendy","marcus"]'::json, 'swords', 4, TRUE),
                ('philosophers', 'Philosophers', 'Socratic + analytical', '["socrates","sophia"]'::json, 'lightbulb', 5, TRUE)
            ON CONFLICT (id) DO NOTHING;
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS roundtable_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                preset_id VARCHAR(50) REFERENCES coach_presets(id) ON DELETE SET NULL,
                title VARCHAR(200),
                coach_ids JSON NOT NULL,
                turn_order JSON,
                current_turn INTEGER DEFAULT 0,
                discussion_mode VARCHAR(20) DEFAULT 'free',
                moderator_id VARCHAR(50) REFERENCES coaches(id),
                llm_config_id VARCHAR(100),
                llm_provider VARCHAR(50),
                llm_model VARCHAR(200),
                llm_temperature DOUBLE PRECISION,
                llm_max_tokens INTEGER,
                kb_timing VARCHAR(20) DEFAULT 'off',
                kb_top_k INTEGER DEFAULT 5,
                kb_max_candidates INTEGER DEFAULT 400,
                message_count INTEGER DEFAULT 0,
                round_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                ended_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    # Ensure moderator mode columns exist for older schemas.
    await conn.execute(
        text(
            """
            ALTER TABLE roundtable_sessions
            ADD COLUMN IF NOT EXISTS discussion_mode VARCHAR(20) DEFAULT 'free',
            ADD COLUMN IF NOT EXISTS moderator_id VARCHAR(50),
            ADD COLUMN IF NOT EXISTS llm_config_id VARCHAR(100),
            ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50),
            ADD COLUMN IF NOT EXISTS llm_model VARCHAR(200),
            ADD COLUMN IF NOT EXISTS llm_temperature DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS llm_max_tokens INTEGER,
            ADD COLUMN IF NOT EXISTS kb_timing VARCHAR(20) DEFAULT 'off',
            ADD COLUMN IF NOT EXISTS kb_top_k INTEGER DEFAULT 5,
            ADD COLUMN IF NOT EXISTS kb_max_candidates INTEGER DEFAULT 400;
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_roundtable_sessions_user_created ON roundtable_sessions(user_id, created_at);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_roundtable_sessions_active ON roundtable_sessions(is_active);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS roundtable_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL REFERENCES roundtable_sessions(id) ON DELETE CASCADE,
                coach_id VARCHAR(50) REFERENCES coaches(id),
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                message_type VARCHAR(20) DEFAULT 'response',
                attachments JSON,
                turn_number INTEGER,
                sequence_in_turn INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    # Ensure message_type exists for older schemas.
    await conn.execute(
        text(
            """
            ALTER TABLE roundtable_messages
            ADD COLUMN IF NOT EXISTS message_type VARCHAR(20) DEFAULT 'response',
            ADD COLUMN IF NOT EXISTS attachments JSON;
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_roundtable_messages_session_created ON roundtable_messages(session_id, created_at);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_roundtable_messages_turn ON roundtable_messages(session_id, turn_number);"
        )
    )

    # Ensure the dedicated host coach exists (for moderated roundtables).
    # Support both legacy (ANALYTICAL) and migration (analytical) coachstyle enums.
    await conn.execute(
        text(
            """
            DO $$
            BEGIN
                INSERT INTO coaches (
                    id, name, avatar_url, description, bio,
                    style, personality_traits, specialty, language,
                    llm_provider, llm_model, system_prompt, temperature, max_tokens,
                    is_premium, is_public, min_subscription_tier,
                    total_sessions, total_messages, is_active, is_default
                ) VALUES (
                    'host',
                    'Roundtable Host',
                    '/images/coaches/host.png',
                    'Roundtable moderator coach',
                    'I facilitate roundtable discussions and summarize viewpoints.',
                    'ANALYTICAL',
                    '["neutral","organized","insightful"]'::json,
                    '["moderation","summarization","facilitation"]'::json,
                    'en',
                    'openai',
                    'gpt-4o-mini',
                    'You are a roundtable moderator. Keep responses concise and structured.',
                    0.7,
                    500,
                    FALSE,
                    TRUE,
                    'free',
                    0,
                    0,
                    TRUE,
                    FALSE
                )
                ON CONFLICT (id) DO NOTHING;
            EXCEPTION WHEN invalid_text_representation THEN
                INSERT INTO coaches (
                    id, name, avatar_url, description, bio,
                    style, personality_traits, specialty, language,
                    llm_provider, llm_model, system_prompt, temperature, max_tokens,
                    is_premium, is_public, min_subscription_tier,
                    total_sessions, total_messages, is_active, is_default
                ) VALUES (
                    'host',
                    'Roundtable Host',
                    '/images/coaches/host.png',
                    'Roundtable moderator coach',
                    'I facilitate roundtable discussions and summarize viewpoints.',
                    'analytical',
                    '["neutral","organized","insightful"]'::json,
                    '["moderation","summarization","facilitation"]'::json,
                    'en',
                    'openai',
                    'gpt-4o-mini',
                    'You are a roundtable moderator. Keep responses concise and structured.',
                    0.7,
                    500,
                    FALSE,
                    TRUE,
                    'free',
                    0,
                    0,
                    TRUE,
                    FALSE
                )
                ON CONFLICT (id) DO NOTHING;
            END $$;
            """
        )
    )
