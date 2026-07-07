from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_billing_schema(conn: AsyncConnection) -> None:
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
