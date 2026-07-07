from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_tenants_schema(conn: AsyncConnection) -> None:
    # Tenants (cloud multi-tenancy)
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE tenantplan AS ENUM ('free', 'starter', 'professional', 'enterprise');
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
                CREATE TYPE tenantstatus AS ENUM ('active', 'suspended', 'trial', 'cancelled');
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
                CREATE TYPE tenantrole AS ENUM ('owner', 'admin', 'member', 'guest');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                slug VARCHAR(100) UNIQUE NOT NULL,
                domain VARCHAR(255),
                logo_url TEXT,
                description TEXT,
                plan tenantplan NOT NULL DEFAULT 'free',
                status tenantstatus NOT NULL DEFAULT 'trial',
                stripe_customer_id VARCHAR(255) UNIQUE,
                stripe_subscription_id VARCHAR(255),
                subscription_expires_at TIMESTAMPTZ,
                trial_ends_at TIMESTAMPTZ,
                max_users INTEGER DEFAULT 5,
                max_projects INTEGER DEFAULT 10,
                max_storage_gb INTEGER DEFAULT 5,
                max_api_calls_per_month INTEGER DEFAULT 10000,
                current_users INTEGER DEFAULT 0,
                current_projects INTEGER DEFAULT 0,
                current_storage_gb INTEGER DEFAULT 0,
                current_api_calls_this_month INTEGER DEFAULT 0,
                settings JSON DEFAULT '{"sso_enabled": false, "enforce_2fa": false, "ip_whitelist": [], "allowed_email_domains": []}'::json,
                billing_email VARCHAR(255),
                billing_address JSON,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                deleted_at TIMESTAMPTZ
            );
            """
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_tenants_slug_active ON tenants(slug, is_active);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_tenants_status ON tenants(status, plan);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenant_members (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id),
                user_id UUID NOT NULL REFERENCES users(id),
                role tenantrole NOT NULL DEFAULT 'member',
                is_active BOOLEAN DEFAULT TRUE,
                invited_by UUID REFERENCES users(id),
                invitation_accepted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )
    await conn.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_tenant_members_tenant_user ON tenant_members(tenant_id, user_id);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_tenant_members_user_active ON tenant_members(user_id, is_active);"
        )
    )
