"""Database bootstrap utilities for local development.

The API currently avoids `Base.metadata.create_all()` at startup due to model
import/metadata issues. For day-to-day local/dev usage we still want a
zero-touch experience, so this module provides an idempotent, Postgres-focused
schema bootstrap for the minimal tables needed by auth + trading journal.
"""

from __future__ import annotations

import os

from sqlalchemy import text

from config import get_settings
from core.database import engine
from core.logging import get_logger

logger = get_logger(__name__)

_TRUTHY = {"1", "true", "yes", "y", "on"}


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY


def should_auto_init_db() -> bool:
    """Return True when we should auto-bootstrap the DB schema."""
    settings = get_settings()

    # Safety: only auto-init in development by default.
    if settings.environment.lower() != "development":
        return False

    env_value = os.getenv("AIWENDY_AUTO_INIT_DB")
    if env_value is None:
        return True
    return _is_truthy(env_value)


async def ensure_dev_schema() -> None:
    """Ensure required tables exist (idempotent)."""
    settings = get_settings()

    if not settings.database_url.lower().startswith("postgres"):
        logger.info(
            "Skipping dev DB bootstrap for non-Postgres database",
            database_url=settings.database_url,
        )
        return

    async with engine.begin() as conn:
        # Ensure UUID generator exists for `gen_random_uuid()`
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto";'))
        # pgvector extension for embedding search
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector";'))

        # Users + sessions (auth)
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE subscriptiontier AS ENUM ('free', 'pro', 'elite', 'enterprise');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    is_email_verified BOOLEAN DEFAULT FALSE,
                    email_verification_token VARCHAR(255),
                    full_name VARCHAR(255),
                    display_name VARCHAR(100),
                    avatar_url TEXT,
                    bio TEXT,
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    language VARCHAR(10) DEFAULT 'en',
                    trading_types JSON DEFAULT '[]'::json,
                    main_concern TEXT,
                    preferred_coach_id VARCHAR(50),
                    preferred_coach_style VARCHAR(50),
                    subscription_tier subscriptiontier DEFAULT 'free' NOT NULL,
                    stripe_customer_id VARCHAR(255),
                    stripe_subscription_id VARCHAR(255),
                    subscription_expires_at TIMESTAMPTZ,
                    openai_api_key TEXT,
                    anthropic_api_key TEXT,
                    api_keys_encrypted JSON DEFAULT '{}'::json,
                    notification_preferences JSON DEFAULT '{"email_daily_summary": false, "email_weekly_report": true, "push_notifications": true, "sms_alerts": false}'::json,
                    privacy_settings JSON DEFAULT '{"share_analytics": true, "public_profile": false}'::json,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    last_login_at TIMESTAMPTZ,
                    login_count INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    deleted_at TIMESTAMPTZ
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS openai_api_key TEXT,
                ADD COLUMN IF NOT EXISTS anthropic_api_key TEXT,
                ADD COLUMN IF NOT EXISTS api_keys_encrypted JSON DEFAULT '{}'::json;
                """
            )
        )

        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);")
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_users_email_active ON users(email, is_active);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_users_subscription ON users(subscription_tier, subscription_expires_at);"
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id),
                    access_token VARCHAR(500) NOT NULL,
                    refresh_token VARCHAR(500) NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent VARCHAR(255),
                    device_info JSON,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NOT NULL,
                    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
                    revoked_at TIMESTAMPTZ
                );
                """
            )
        )

        await conn.execute(
            text("ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS device_info JSON;")
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_sessions_access_token ON user_sessions(access_token);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at ON user_sessions(expires_at);"
            )
        )

        # Projects (workspaces)
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    is_default BOOLEAN DEFAULT FALSE,
                    is_archived BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        # Ensure newer columns exist when upgrading an existing database
        await conn.execute(
            text(
                """
                ALTER TABLE projects
                ADD COLUMN IF NOT EXISTS description TEXT,
                ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_projects_user_updated ON projects(user_id, updated_at);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_projects_user_default ON projects(user_id, is_default);"
            )
        )

        # Coaches + chat history (sessions/messages)
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE coachstyle AS ENUM ('EMPATHETIC', 'DISCIPLINED', 'ANALYTICAL', 'MOTIVATIONAL', 'SOCRATIC');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE llmprovider AS ENUM ('openai', 'anthropic', 'local', 'custom');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS coaches (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    avatar_url TEXT,
                    description TEXT,
                    bio TEXT,
                    style coachstyle NOT NULL,
                    personality_traits JSON DEFAULT '[]'::json,
                    specialty JSON DEFAULT '[]'::json,
                    language VARCHAR(10) DEFAULT 'en',
                    llm_provider llmprovider DEFAULT 'openai',
                    llm_model VARCHAR(100) NOT NULL,
                    system_prompt TEXT NOT NULL,
                    temperature FLOAT DEFAULT 0.7,
                    max_tokens INTEGER DEFAULT 2000,
                    voice_id VARCHAR(100),
                    voice_settings JSON,
                    is_premium BOOLEAN DEFAULT FALSE,
                    is_public BOOLEAN DEFAULT TRUE,
                    min_subscription_tier VARCHAR(20) DEFAULT 'free',
                    created_by UUID,
                    total_sessions INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    avg_rating FLOAT,
                    rating_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_coaches_style_active ON coaches(style, is_active);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_coaches_public_premium ON coaches(is_public, is_premium);"
            )
        )

        # Ensure default coaches exist for dev (all 5 coaches)
        await conn.execute(
            text(
                """
                INSERT INTO coaches (
                    id, name, description, bio, style, personality_traits, specialty, language,
                    llm_provider, llm_model, system_prompt, temperature, max_tokens,
                    is_premium, is_public, is_active, is_default, min_subscription_tier
                ) VALUES
                (
                    'wendy',
                    'Wendy Rhodes',
                    '温和共情型教练，专注于情绪管理和心理韧性',
                    'Wendy 是一位资深交易心理教练，擅长帮助交易者处理情绪波动、克服恐惧与贪婪。',
                    'EMPATHETIC',
                    '["温暖","耐心","理解力强","洞察力深","支持性强"]'::json,
                    '["情绪管理","心理韧性","信心重建","压力调节","创伤修复"]'::json,
                    'zh',
                    'openai',
                    'gpt-4o-mini',
                    '你是 Wendy Rhodes，一位温和共情型的交易心理教练。你的风格温暖、理解、支持。请帮助交易者提升情绪管理、纪律与心理韧性。',
                    0.7,
                    2000,
                    FALSE,
                    TRUE,
                    TRUE,
                    TRUE,
                    'free'
                ),
                (
                    'marcus',
                    'Marcus Steel',
                    '严厉纪律型教练，强调风控和执行力',
                    'Marcus Steel 是一位前对冲基金经理，现专注于交易纪律培训。',
                    'DISCIPLINED',
                    '["严格","直接","果断","要求高","结果导向"]'::json,
                    '["风险管理","纪律执行","止损策略","规则制定","习惯养成"]'::json,
                    'zh',
                    'openai',
                    'gpt-4o-mini',
                    '你是 Marcus Steel，一位严厉纪律型的交易教练。你的风格直接、严格、不留情面。核心原则：纪律至上，直面真相，执行力，责任感，系统思维。',
                    0.5,
                    1500,
                    FALSE,
                    TRUE,
                    TRUE,
                    FALSE,
                    'free'
                ),
                (
                    'sophia',
                    'Dr. Sophia Chen',
                    '数据分析型教练，用数据驱动决策',
                    'Dr. Sophia Chen 拥有金融工程博士学位，专注于量化分析和数据驱动的交易改进。',
                    'ANALYTICAL',
                    '["理性","精确","客观","系统化","数据导向"]'::json,
                    '["绩效分析","模式识别","统计优化","回测分析","量化改进"]'::json,
                    'zh',
                    'openai',
                    'gpt-4o-mini',
                    '你是 Dr. Sophia Chen，一位数据分析型交易教练。你用数据和逻辑帮助交易者改进。核心原则：数据驱动，客观理性，量化思维，模式识别，持续优化。',
                    0.4,
                    2000,
                    FALSE,
                    TRUE,
                    TRUE,
                    FALSE,
                    'free'
                ),
                (
                    'alex',
                    'Alex Thunder',
                    '激励鼓舞型教练，激发潜能和斗志',
                    'Alex Thunder 是一位充满激情的励志教练，曾帮助数百位交易者重燃斗志。',
                    'MOTIVATIONAL',
                    '["激情","乐观","鼓舞人心","充满能量","积极向上"]'::json,
                    '["信心建设","目标设定","动力激发","成功心态","突破限制"]'::json,
                    'zh',
                    'openai',
                    'gpt-4o-mini',
                    '你是 Alex Thunder，一位激励鼓舞型交易教练。你的任务是激发交易者的潜能和斗志。核心原则：积极思维，赋能信念，行动导向，庆祝进步，未来聚焦。',
                    0.8,
                    2000,
                    TRUE,
                    TRUE,
                    TRUE,
                    FALSE,
                    'pro'
                ),
                (
                    'socrates',
                    'Socrates',
                    '苏格拉底式教练，通过提问引导自我发现',
                    '以古希腊哲学家苏格拉底命名，这位教练采用经典的苏格拉底式提问法。',
                    'SOCRATIC',
                    '["智慧","耐心","深刻","引导性","哲学性"]'::json,
                    '["自我认知","批判思维","深度反思","信念挑战","智慧培养"]'::json,
                    'zh',
                    'openai',
                    'gpt-4o-mini',
                    '你是 Socrates，一位苏格拉底式交易教练。你通过提问引导交易者自我发现。核心原则：提问而非告知，自我发现，批判思维，深度探索，智慧生成。',
                    0.6,
                    1800,
                    TRUE,
                    TRUE,
                    TRUE,
                    FALSE,
                    'pro'
                )
                ON CONFLICT (id) DO NOTHING;
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    coach_id VARCHAR(50) NOT NULL REFERENCES coaches(id),
                    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                    title VARCHAR(200),
                    context JSON,
                    mood_before INTEGER,
                    mood_after INTEGER,
                    message_count INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    user_rating INTEGER,
                    user_feedback TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    ended_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE chat_sessions
                ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_created ON chat_sessions(user_id, created_at);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_project_created ON chat_sessions(user_id, project_id, created_at);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chat_sessions_coach_active ON chat_sessions(coach_id, is_active);"
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    token_count INTEGER,
                    has_attachments BOOLEAN DEFAULT FALSE,
                    message_metadata JSON,
                    detected_emotions JSON,
                    detected_patterns JSON,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created ON chat_messages(session_id, created_at);"
            )
        )

        # Ensure has_attachments column exists for older schemas
        await conn.execute(
            text(
                """
                ALTER TABLE chat_messages
                ADD COLUMN IF NOT EXISTS has_attachments BOOLEAN DEFAULT FALSE;
                """
            )
        )

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

        # Knowledge base (documents + chunks)
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                    title VARCHAR(255) NOT NULL,
                    source_type VARCHAR(50) DEFAULT 'text',
                    source_name TEXT,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    chunk_count INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    deleted_at TIMESTAMPTZ
                );
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_kb_documents_user_project_created ON knowledge_documents(user_id, project_id, created_at);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_kb_documents_user_title ON knowledge_documents(user_id, title);"
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding_vector vector,
                    embedding_dim INTEGER,
                    embedding_model VARCHAR(100),
                    embedding_provider VARCHAR(50),
                    token_count INTEGER,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_kb_chunks_document_index ON knowledge_chunks(document_id, chunk_index);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_kb_chunks_user_project_created ON knowledge_chunks(user_id, project_id, created_at);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_kb_chunks_user_project_dim ON knowledge_chunks(user_id, project_id, embedding_dim);"
            )
        )

        # Ensure the vector column exists for older schemas
        await conn.execute(
            text(
                "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector;"
            )
        )

        # Partial ANN indexes per common embedding dims.
        #
        # Note: pgvector requires a fixed-dimension vector type for ivfflat/hnsw indexes.
        # Our schema uses `vector` without a fixed dimension to support multiple providers/models,
        # so we build expression indexes that cast to a fixed dimension and guard with a WHERE clause.
        # If index creation fails (e.g., older pgvector, inconsistent data), we log and continue.
        for dim, lists in ((1536, 100), (768, 50)):
            stmt = f"""
                CREATE INDEX IF NOT EXISTS ix_kb_chunks_embedding_vector_cosine_{dim}
                ON knowledge_chunks
                USING ivfflat ((embedding_vector::vector({dim})) vector_cosine_ops)
                WITH (lists = {lists})
                WHERE embedding_dim = {dim} AND embedding_vector IS NOT NULL;
            """
            try:
                async with conn.begin_nested():
                    await conn.execute(text(stmt))
            except Exception as e:
                logger.warning(
                    "Skipping knowledge_chunks ivfflat index creation",
                    embedding_dim=dim,
                    error=str(e),
                )

        # Journals (trading journal)
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS journals (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

                    -- Trade information
                    trade_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    symbol VARCHAR(20) NOT NULL,
                    market VARCHAR(20),
                    direction VARCHAR(10) NOT NULL CHECK (direction IN ('long', 'short')),

                    -- Entry/Exit
                    entry_time TIMESTAMP WITH TIME ZONE,
                    entry_price FLOAT,
                    position_size FLOAT,
                    exit_time TIMESTAMP WITH TIME ZONE,
                    exit_price FLOAT,

                    -- Results
                    result VARCHAR(10) DEFAULT 'open' CHECK (result IN ('win', 'loss', 'breakeven', 'open')),
                    pnl_amount FLOAT,
                    pnl_percentage FLOAT,

                    -- Risk management
                    stop_loss FLOAT,
                    take_profit FLOAT,
                    risk_reward_ratio FLOAT,

                    -- Emotions (1-5 scale)
                    emotion_before INTEGER CHECK (emotion_before >= 1 AND emotion_before <= 5),
                    emotion_during INTEGER CHECK (emotion_during >= 1 AND emotion_during <= 5),
                    emotion_after INTEGER CHECK (emotion_after >= 1 AND emotion_after <= 5),

                    -- Psychology
                    confidence_level INTEGER CHECK (confidence_level >= 1 AND confidence_level <= 5),
                    stress_level INTEGER CHECK (stress_level >= 1 AND stress_level <= 5),
                    followed_rules BOOLEAN DEFAULT TRUE,
                    rule_violations JSONB DEFAULT '[]',

                    -- Notes
                    setup_description TEXT,
                    exit_reason TEXT,
                    lessons_learned TEXT,
                    notes TEXT,

                    -- AI Analysis
                    ai_insights TEXT,
                    detected_patterns JSONB,

                    -- Tags and categories
                    tags JSONB DEFAULT '[]',
                    strategy_name VARCHAR(100),

                    -- Attachments
                    screenshots JSONB DEFAULT '[]',

                    -- Timestamps
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP WITH TIME ZONE
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE journals
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS journal_templates (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

                    -- Template info
                    name VARCHAR(100) NOT NULL,
                    description TEXT,

                    -- Default values
                    default_values JSONB NOT NULL,

                    -- Usage
                    usage_count INTEGER DEFAULT 0,
                    last_used_at TIMESTAMP WITH TIME ZONE,

                    -- Timestamps
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_journals_user_date ON journals(user_id, trade_date);"
            )
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_journals_symbol ON journals(symbol);")
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_journals_result ON journals(result);")
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_journals_user_result ON journals(user_id, result);"
            )
        )

        # Add project grouping to journals when projects exist
        await conn.execute(
            text(
                """
                ALTER TABLE journals
                ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_journals_user_project_date
                ON journals(user_id, project_id, trade_date);
                """
            )
        )

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

        # Subscriptions & payments
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE plantype AS ENUM ('free', 'pro', 'elite', 'enterprise');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE billinginterval AS ENUM ('monthly', 'yearly', 'lifetime');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE paymentstatus AS ENUM ('pending', 'processing', 'succeeded', 'failed', 'canceled', 'refunded');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )
        await conn.execute(
            text(
                """
                DO $$ BEGIN
                    CREATE TYPE subscriptionstatus AS ENUM (
                        'active',
                        'trialing',
                        'past_due',
                        'canceled',
                        'unpaid',
                        'incomplete',
                        'incomplete_expired'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

                    plan_type plantype NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,

                    monthly_price NUMERIC(10, 2) NOT NULL,
                    yearly_price NUMERIC(10, 2) NOT NULL,
                    monthly_price_cny NUMERIC(10, 2),
                    yearly_price_cny NUMERIC(10, 2),

                    stripe_monthly_price_id VARCHAR(255),
                    stripe_yearly_price_id VARCHAR(255),
                    stripe_product_id VARCHAR(255),

                    features JSONB DEFAULT '[]'::jsonb,
                    limits JSONB DEFAULT '{}'::jsonb,

                    max_journals_per_day INTEGER DEFAULT -1,
                    max_ai_chats_per_day INTEGER DEFAULT -1,
                    max_reports_per_month INTEGER DEFAULT -1,
                    max_coaches INTEGER DEFAULT 3,

                    has_premium_coaches BOOLEAN DEFAULT FALSE,
                    has_api_access BOOLEAN DEFAULT FALSE,
                    has_priority_support BOOLEAN DEFAULT FALSE,
                    has_custom_reports BOOLEAN DEFAULT FALSE,
                    has_team_features BOOLEAN DEFAULT FALSE,
                    has_white_label BOOLEAN DEFAULT FALSE,

                    is_popular BOOLEAN DEFAULT FALSE,
                    display_order INTEGER DEFAULT 0,
                    badge_text VARCHAR(50),

                    is_active BOOLEAN DEFAULT TRUE,
                    is_visible BOOLEAN DEFAULT TRUE,

                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    plan_id UUID NOT NULL REFERENCES subscription_plans(id),

                    status subscriptionstatus NOT NULL DEFAULT 'incomplete',
                    billing_interval billinginterval NOT NULL,

                    stripe_subscription_id VARCHAR(255) UNIQUE,
                    stripe_customer_id VARCHAR(255),
                    stripe_payment_method_id VARCHAR(255),

                    trial_start TIMESTAMPTZ,
                    trial_end TIMESTAMPTZ,
                    current_period_start TIMESTAMPTZ,
                    current_period_end TIMESTAMPTZ,
                    canceled_at TIMESTAMPTZ,
                    ended_at TIMESTAMPTZ,

                    next_payment_amount NUMERIC(10, 2),
                    next_payment_date TIMESTAMPTZ,

                    metadata JSONB,
                    cancel_reason TEXT,

                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE SET NULL,

                    amount NUMERIC(10, 2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'USD',
                    status paymentstatus NOT NULL DEFAULT 'pending',

                    stripe_payment_intent_id VARCHAR(255) UNIQUE,
                    stripe_invoice_id VARCHAR(255),
                    stripe_charge_id VARCHAR(255),

                    payment_method_type VARCHAR(50),
                    last_four VARCHAR(4),
                    card_brand VARCHAR(50),

                    description TEXT,
                    failure_reason TEXT,
                    receipt_url TEXT,

                    metadata JSONB,

                    paid_at TIMESTAMPTZ,
                    failed_at TIMESTAMPTZ,
                    refunded_at TIMESTAMPTZ,

                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

                    code VARCHAR(50) NOT NULL UNIQUE,
                    description TEXT,

                    discount_type VARCHAR(20) NOT NULL,
                    discount_amount NUMERIC(10, 2) NOT NULL,

                    applicable_plans JSONB DEFAULT '[]'::jsonb,

                    max_uses INTEGER,
                    uses_count INTEGER DEFAULT 0,
                    max_uses_per_user INTEGER DEFAULT 1,

                    valid_from TIMESTAMPTZ NOT NULL,
                    valid_until TIMESTAMPTZ,

                    stripe_coupon_id VARCHAR(255),
                    stripe_promotion_code_id VARCHAR(255),

                    is_active BOOLEAN DEFAULT TRUE,

                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_subscription_plans_active_visible ON subscription_plans(is_active, is_visible, display_order);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_user_status ON user_subscriptions(user_id, status);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_id ON user_subscriptions(stripe_subscription_id);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_payments_user_status ON payments(user_id, status);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_payments_stripe_intent ON payments(stripe_payment_intent_id);"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_promo_codes_code_active ON promo_codes(code, is_active);"
            )
        )

        # Default plans (idempotent)
        await conn.execute(
            text(
                """
                INSERT INTO subscription_plans (
                    plan_type,
                    name,
                    description,
                    monthly_price,
                    yearly_price,
                    features,
                    limits,
                    max_journals_per_day,
                    max_ai_chats_per_day,
                    max_reports_per_month,
                    max_coaches,
                    has_premium_coaches,
                    has_api_access,
                    has_priority_support,
                    has_custom_reports,
                    has_team_features,
                    has_white_label,
                    is_popular,
                    display_order,
                    badge_text,
                    is_active,
                    is_visible
                ) VALUES
                (
                    'free',
                    '免费版',
                    '适合刚开始的交易者',
                    0,
                    0,
                    '["每日 3 条交易日志","基础 AI 分析","3 个基础教练","基础报告"]'::jsonb,
                    '{"max_journals_per_day": 3, "max_ai_chats_per_day": 10, "max_reports_per_month": 1, "max_coaches": 3}'::jsonb,
                    3,
                    10,
                    1,
                    3,
                    FALSE,
                    FALSE,
                    FALSE,
                    FALSE,
                    FALSE,
                    FALSE,
                    FALSE,
                    0,
                    NULL,
                    TRUE,
                    TRUE
                ),
                (
                    'pro',
                    '专业版',
                    '适合认真提升的交易者',
                    79,
                    790,
                    '["无限交易日志","无限 AI 对话","全部教练","周报/月报","优先支持"]'::jsonb,
                    '{"max_journals_per_day": -1, "max_ai_chats_per_day": -1, "max_reports_per_month": -1, "max_coaches": 5}'::jsonb,
                    -1,
                    -1,
                    -1,
                    5,
                    TRUE,
                    FALSE,
                    TRUE,
                    TRUE,
                    FALSE,
                    FALSE,
                    TRUE,
                    1,
                    '最受欢迎',
                    TRUE,
                    TRUE
                ),
                (
                    'elite',
                    '精英版',
                    '适合专业交易者与团队',
                    149,
                    1490,
                    '["Pro 全部功能","1v1 辅导（预留）","自定义教练（预留）","团队协作（预留）","API 访问（预留）"]'::jsonb,
                    '{"max_journals_per_day": -1, "max_ai_chats_per_day": -1, "max_reports_per_month": -1, "max_coaches": -1}'::jsonb,
                    -1,
                    -1,
                    -1,
                    -1,
                    TRUE,
                    TRUE,
                    TRUE,
                    TRUE,
                    TRUE,
                    FALSE,
                    FALSE,
                    2,
                    '最佳价值',
                    TRUE,
                    TRUE
                )
                ON CONFLICT (plan_type) DO NOTHING;
                """
            )
        )


async def maybe_auto_init_db() -> None:
    """Auto-bootstrap DB schema when enabled."""
    if not should_auto_init_db():
        return

    logger.info("Auto-initializing DB schema (development)")
    await ensure_dev_schema()
    logger.info("DB schema ready")
