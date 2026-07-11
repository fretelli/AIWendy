"""Read-only access to the existing Tushare PostgreSQL schema.

KeelTrader AgentOS never stores or uses a Tushare token. It reads data that
has already been synchronized by /opt/services/tushare.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings


_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

ALLOWED_TABLES = {
    "stock_basic",
    "stock_daily",
    "stock_daily_adj",
    "stock_weekly",
    "stock_monthly",
    "fina_indicator",
    "income",
    "balancesheet",
    "cashflow",
    "dividend",
    "trade_cal",
    "index_basic",
    "index_global",
    "fund_basic",
    "fund_nav",
    "cn_cpi",
    "cn_ppi",
    "cn_pmi",
    "cn_gdp",
    "shibor",
    "lpr",
}

_tushare_session_factory: async_sessionmaker[AsyncSession] | None = None
_tushare_session_url: str | None = None


def _get_tushare_session_factory() -> async_sessionmaker[AsyncSession] | None:
    """Return a lazily initialized read-only Tushare DB session factory."""
    global _tushare_session_factory, _tushare_session_url

    url = get_settings().tushare_database_url
    if not url:
        return None
    if _tushare_session_factory is not None and _tushare_session_url == url:
        return _tushare_session_factory

    engine = create_async_engine(
        url, pool_pre_ping=True, pool_size=3, max_overflow=1, pool_timeout=15, pool_recycle=1800,
        connect_args={"server_settings": {
            "application_name": "keeltrader-tushare-reader",
            "idle_in_transaction_session_timeout": "60000",
            "statement_timeout": "30000",
        }} if "+asyncpg" in url else {},
    )
    _tushare_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _tushare_session_url = url
    return _tushare_session_factory


class TushareReadService:
    """Small, safe query facade for the synchronized `tushare` schema."""

    def __init__(self, session: AsyncSession, schema: str = "tushare"):
        if not _IDENT_RE.match(schema):
            raise ValueError("Invalid Tushare schema name")
        self.session = session
        self.schema = schema
        self._table_exists_cache: dict[str, bool] = {}

    @asynccontextmanager
    async def _session_scope(self):
        factory = _get_tushare_session_factory()
        if factory is None:
            if self.session is None:
                raise RuntimeError("No Tushare database session is available")
            yield self.session
            return

        async with factory() as session:
            try:
                yield session
            finally:
                await session.close()

    async def table_exists(self, table: str) -> bool:
        """Return whether a synchronized Tushare table exists in the current DB."""
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Tushare table is not allowlisted: {table}")
        cached = self._table_exists_cache.get(table)
        if cached is not None:
            return cached
        q = text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema AND table_name = :table
            )
            """
        )
        async with self._session_scope() as session:
            exists = bool((await session.execute(q, {"schema": self.schema, "table": table})).scalar())
        self._table_exists_cache[table] = exists
        return exists

    async def _execute_mappings(self, query, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a read query and degrade gracefully when upstream tables are absent."""
        async with self._session_scope() as session:
            try:
                rows = (await session.execute(query, params)).mappings().all()
                return [_json_safe(dict(r)) for r in rows]
            except (ProgrammingError, DBAPIError) as exc:
                message = str(exc).lower()
                if "undefinedtableerror" in message or "does not exist" in message:
                    await session.rollback()
                    return []
                raise

    async def stock_profile(self, symbol: str) -> dict[str, Any] | None:
        """Return stock_basic row for a ts_code or name fragment."""
        if not await self.table_exists("stock_basic"):
            return None
        q = text(
            f"""
            SELECT *
            FROM {self.schema}.stock_basic
            WHERE ts_code = :symbol OR name ILIKE :name
            ORDER BY ts_code
            LIMIT 1
            """
        )
        rows = await self._execute_mappings(q, {"symbol": symbol, "name": f"%{symbol}%"})
        return rows[0] if rows else None

    async def search_companies(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search the complete A-share company catalog without model usage."""
        if not await self.table_exists("stock_basic"):
            return []
        value = query.strip()
        limit = max(1, min(limit, 50))
        q = text(
            f"""
            SELECT ts_code, symbol, name, area, industry, market, list_date
            FROM {self.schema}.stock_basic
            WHERE :query = '' OR ts_code ILIKE :pattern OR symbol ILIKE :pattern OR name ILIKE :pattern
            ORDER BY CASE WHEN ts_code = :query OR symbol = :query OR name = :query THEN 0 ELSE 1 END, ts_code
            LIMIT :limit
            """
        )
        return await self._execute_mappings(q, {"query": value, "pattern": f"%{value}%", "limit": limit})

    async def daily_bars(self, symbol: str, limit: int = 120, adjusted: bool = True) -> list[dict[str, Any]]:
        """Return recent daily bars for a stock."""
        table = "stock_daily_adj" if adjusted else "stock_daily"
        if not await self.table_exists(table):
            return []
        limit = max(1, min(limit, 1000))
        q = text(
            f"""
            SELECT *
            FROM {self.schema}.{table}
            WHERE ts_code = :symbol
            ORDER BY trade_date DESC
            LIMIT :limit
            """
        )
        return await self._execute_mappings(q, {"symbol": symbol, "limit": limit})

    async def financial_indicators(self, symbol: str, limit: int = 8) -> list[dict[str, Any]]:
        """Return recent financial indicator rows."""
        if not await self.table_exists("fina_indicator"):
            return []
        limit = max(1, min(limit, 40))
        q = text(
            f"""
            SELECT *
            FROM {self.schema}.fina_indicator
            WHERE ts_code = :symbol
            ORDER BY end_date DESC
            LIMIT :limit
            """
        )
        return await self._execute_mappings(q, {"symbol": symbol, "limit": limit})

    async def company_financials(self, symbol: str, limit: int = 12) -> dict[str, list[dict[str, Any]]]:
        """Return canonical statement rows used by the deterministic dossier engine."""
        result: dict[str, list[dict[str, Any]]] = {}
        for table in ("fina_indicator", "income", "balancesheet", "cashflow", "dividend"):
            if not await self.table_exists(table):
                result[table] = []
                continue
            order = "end_date" if table != "dividend" else "end_date"
            q = text(
                f"SELECT * FROM {self.schema}.{table} WHERE ts_code = :symbol "
                f"ORDER BY {order} DESC, ann_date DESC NULLS LAST, updated_at DESC NULLS LAST LIMIT :limit"
            )
            result[table] = await self._execute_mappings(q, {"symbol": symbol, "limit": max(1, min(limit, 40))})
        result["stock_daily"] = await self.daily_bars(symbol, limit=260, adjusted=False)
        return result

    async def industry_peers(self, industry: str, exclude_symbol: str, period: str | None = None,
                             limit: int = 20) -> list[dict[str, Any]]:
        if not industry or not await self.table_exists("stock_basic") or not await self.table_exists("fina_indicator"):
            return []
        q = text(f"""
            SELECT DISTINCT ON (f.ts_code) f.ts_code, b.name, f.end_date, f.roe, f.grossprofit_margin,
                   f.netprofit_margin, f.debt_to_assets
            FROM {self.schema}.fina_indicator f
            JOIN {self.schema}.stock_basic b ON b.ts_code = f.ts_code
            WHERE b.industry = :industry AND f.ts_code <> :symbol
              AND (:period IS NULL OR f.end_date = :period)
            ORDER BY f.ts_code, f.end_date DESC, f.ann_date DESC NULLS LAST, f.updated_at DESC NULLS LAST
            LIMIT :limit
        """)
        return await self._execute_mappings(q, {
            "industry": industry, "symbol": exclude_symbol, "period": period, "limit": limit,
        })

    async def query_table(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Query an allowlisted Tushare table with equality filters."""
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Tushare table is not allowlisted: {table}")
        if not await self.table_exists(table):
            return []
        filters = filters or {}
        limit = max(1, min(limit, 500))

        clauses = []
        params: dict[str, Any] = {"limit": limit}
        for idx, (key, value) in enumerate(filters.items()):
            if not _IDENT_RE.match(key):
                raise ValueError(f"Invalid filter column: {key}")
            param_key = f"p{idx}"
            clauses.append(f"{key} = :{param_key}")
            params[param_key] = value

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        q = text(f"SELECT * FROM {self.schema}.{table} {where_sql} LIMIT :limit")
        return await self._execute_mappings(q, params)


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value
