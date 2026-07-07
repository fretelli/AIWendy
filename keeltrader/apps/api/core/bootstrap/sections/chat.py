from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_chat_schema(conn: AsyncConnection) -> None:
    # Coaches + chat history (sessions/messages)
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE coachstyle AS ENUM ('empathetic', 'disciplined', 'analytical', 'motivational', 'socratic');
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
                'empathetic',
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
                'disciplined',
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
                'analytical',
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
                'motivational',
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
                'socratic',
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

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS chat_attachments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                message_id UUID NOT NULL REFERENCES chat_messages(id),
                attachment_type VARCHAR(20) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type VARCHAR(100) NOT NULL,
                storage_path TEXT NOT NULL,
                extracted_text TEXT,
                transcription TEXT,
                thumbnail_base64 TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_chat_attachments_message ON chat_attachments(message_id);"
        )
    )
