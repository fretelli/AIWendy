"""Add moderator mode support to roundtable discussions

Revision ID: 008
Revises: 007
Create Date: 2025-01-04

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add the dedicated host coach
    op.execute(
        """
        INSERT INTO coaches (
            id, name, avatar_url, description, bio,
            style, personality_traits, specialty, language,
            llm_provider, llm_model, system_prompt, temperature, max_tokens,
            is_premium, is_public, min_subscription_tier,
            total_sessions, total_messages, is_active, is_default
        ) VALUES (
            'host',
            '圆桌主持人',
            '/images/coaches/host.png',
            '专业的讨论主持人，擅长总结观点、引导深入、控制节奏',
            '我是圆桌讨论的专属主持人，负责开场破题、总结各位教练的观点、提出深化问题、控制讨论节奏，并在最后给出综合建议。',
            'analytical',
            '["neutral", "organized", "insightful", "articulate"]',
            '["moderation", "summarization", "facilitation", "synthesis"]',
            'zh',
            'openai',
            'gpt-4o-mini',
            '你是一位专业的圆桌讨论主持人。你的职责是：

1. **开场破题**：简要介绍讨论主题，预告将邀请哪些教练从哪些角度分析
2. **总结观点**：每轮讨论后总结各教练的核心观点，指出共识和分歧
3. **深化引导**：提出深化问题，引导讨论更加深入
4. **控制节奏**：根据问题特点，安排合理的发言顺序
5. **综合建议**：讨论结束时，给出综合性的建议和行动方向

沟通风格：
- 保持中立、客观、专业
- 语言清晰、有条理
- 每次发言控制在 3-5 句话
- 善于发现不同观点之间的联系和冲突
- 引导用户思考，而非直接给出答案',
            0.7,
            500,
            false,
            true,
            'free',
            0,
            0,
            true,
            false
        )
        ON CONFLICT (id) DO NOTHING
    """
    )

    # 2. Add discussion_mode column to roundtable_sessions
    # 'free' = free discussion (existing mode)
    # 'moderated' = moderated mode with host
    op.add_column(
        "roundtable_sessions",
        sa.Column(
            "discussion_mode", sa.String(20), nullable=True, server_default="free"
        ),
    )

    # 3. Add moderator_id column to roundtable_sessions
    # References the coach who acts as moderator (default is 'host')
    op.add_column(
        "roundtable_sessions", sa.Column("moderator_id", sa.String(50), nullable=True)
    )

    # Add foreign key for moderator_id
    op.create_foreign_key(
        "fk_roundtable_sessions_moderator",
        "roundtable_sessions",
        "coaches",
        ["moderator_id"],
        ["id"],
    )

    # 4. Add message_type column to roundtable_messages
    # 'response' = regular coach response
    # 'opening' = moderator opening
    # 'summary' = moderator round summary
    # 'closing' = moderator closing remarks
    op.add_column(
        "roundtable_messages",
        sa.Column(
            "message_type", sa.String(20), nullable=True, server_default="response"
        ),
    )


def downgrade():
    # Remove message_type column
    op.drop_column("roundtable_messages", "message_type")

    # Remove foreign key and moderator_id column
    op.drop_constraint(
        "fk_roundtable_sessions_moderator", "roundtable_sessions", type_="foreignkey"
    )
    op.drop_column("roundtable_sessions", "moderator_id")

    # Remove discussion_mode column
    op.drop_column("roundtable_sessions", "discussion_mode")

    # Remove host coach
    op.execute("DELETE FROM coaches WHERE id = 'host'")
