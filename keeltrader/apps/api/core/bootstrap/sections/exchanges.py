from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_exchanges_schema(conn: AsyncConnection) -> None:
    # Exchange connections + raw trades
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE exchangetype AS ENUM ('okx', 'bybit', 'coinbase', 'kraken');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS exchange_connections (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                exchange_type exchangetype NOT NULL,
                name VARCHAR(100),
                api_key_encrypted TEXT NOT NULL,
                api_secret_encrypted TEXT NOT NULL,
                passphrase_encrypted TEXT,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                is_testnet BOOLEAN DEFAULT FALSE NOT NULL,
                sync_symbols JSONB DEFAULT '[]'::jsonb,
                last_sync_at TIMESTAMPTZ,
                last_trade_sync_at TIMESTAMPTZ,
                last_error TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    await conn.execute(
        text(
            """
            ALTER TABLE exchange_connections
            ADD COLUMN IF NOT EXISTS sync_symbols JSONB DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS last_trade_sync_at TIMESTAMPTZ;
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_exchange_connections_user_id ON exchange_connections(user_id);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_exchange_connections_user_exchange ON exchange_connections(user_id, exchange_type);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS exchange_trades (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                exchange_connection_id UUID NOT NULL REFERENCES exchange_connections(id) ON DELETE CASCADE,
                journal_id UUID REFERENCES journals(id) ON DELETE SET NULL,
                exchange_trade_id VARCHAR(200) NOT NULL,
                symbol VARCHAR(50) NOT NULL,
                side VARCHAR(10),
                price FLOAT,
                amount FLOAT,
                cost FLOAT,
                fee_cost FLOAT,
                fee_currency VARCHAR(20),
                fee_rate FLOAT,
                trade_timestamp TIMESTAMPTZ,
                raw JSONB,
                is_imported BOOLEAN DEFAULT FALSE NOT NULL,
                imported_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_exchange_trades_connection_trade_id
            ON exchange_trades(exchange_connection_id, exchange_trade_id);
            """
        )
    )
    await conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_exchange_trades_user_time
            ON exchange_trades(user_id, trade_timestamp);
            """
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_exchange_trades_symbol ON exchange_trades(symbol);"
        )
    )
