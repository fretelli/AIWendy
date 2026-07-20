"""Read-only access to the existing Tushare PostgreSQL schema.

KeelTrader AgentOS never stores or uses a Tushare token. It reads data that
has already been synchronized by /opt/services/tushare.
"""

from __future__ import annotations

import asyncio
import copy
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
import re
import time
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
    "fund_share",
    "margin",
    "margin_detail",
    "stk_limit",
    "moneyflow_mkt_dc",
    "cn_cpi",
    "cn_ppi",
    "cn_pmi",
    "cn_gdp",
    "shibor",
    "lpr",
    "top10_floatholders",
}

_tushare_session_factory: async_sessionmaker[AsyncSession] | None = None
_tushare_session_url: str | None = None
_market_capital_cache: dict[int, tuple[float, dict[str, Any]]] = {}
_MARKET_CAPITAL_CACHE_SECONDS = 300


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
                if "undefinedtableerror" in message or ("relation" in message and "does not exist" in message):
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
        period_clause = "AND f.end_date = :period" if period else ""
        q = text(f"""
            SELECT DISTINCT ON (f.ts_code) f.ts_code, b.name, f.end_date, f.roe, f.grossprofit_margin,
                   f.netprofit_margin, f.debt_to_assets
            FROM {self.schema}.fina_indicator f
            JOIN {self.schema}.stock_basic b ON b.ts_code = f.ts_code
            WHERE b.industry = :industry AND f.ts_code <> :symbol
              {period_clause}
            ORDER BY f.ts_code, f.end_date DESC, f.ann_date DESC NULLS LAST, f.updated_at DESC NULLS LAST
            LIMIT :limit
        """)
        params = {"industry": industry, "symbol": exclude_symbol, "limit": limit}
        if period:
            params["period"] = period
        return await self._execute_mappings(q, params)

    async def holder_source_watermark(self) -> str | None:
        """Return a cheap watermark for change detection by the holder inbox worker."""
        if not await self.table_exists("top10_floatholders"):
            return None
        q = text(f"SELECT MAX(updated_at) FROM {self.schema}.top10_floatholders")
        async with self._session_scope() as session:
            value = (await session.execute(q)).scalar()
        return _json_safe(value) if value else None

    async def search_holders(self, query: str, limit: int = 30) -> list[dict[str, Any]]:
        """Search raw shareholder names and return coverage metadata without filtering types."""
        if not await self.table_exists("top10_floatholders"):
            return []
        value = query.strip()
        if not value:
            return []
        limit = max(1, min(limit, 50))
        q = text(f"""
            SELECT holder_name, COALESCE(holder_type, '未知') AS holder_type,
                   COUNT(DISTINCT ts_code) AS stock_count,
                   MIN(end_date) AS first_end_date,
                   MAX(end_date) AS last_end_date,
                   MAX(ann_date) AS last_ann_date,
                   CASE WHEN holder_name = :query THEN true ELSE false END AS exact_match
            FROM {self.schema}.top10_floatholders
            WHERE holder_name ILIKE :pattern
            GROUP BY holder_name, COALESCE(holder_type, '未知')
            ORDER BY CASE WHEN holder_name = :query THEN 0 ELSE 1 END,
                     MAX(end_date) DESC, COUNT(DISTINCT ts_code) DESC, holder_name
            LIMIT :limit
        """)
        return await self._execute_mappings(q, {
            "query": value, "pattern": f"%{value}%", "limit": limit,
        })

    async def holder_current_positions(
        self,
        holder_names: list[str],
        holder_type: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return positions present in each company's own latest disclosed period."""
        if not await self.table_exists("top10_floatholders"):
            return {"items": [], "total": 0, "source_available": False, "source_as_of": None}
        names = [name.strip() for name in holder_names if name.strip()]
        if not names:
            return {"items": [], "total": 0, "source_available": True, "source_as_of": None}
        limit, offset = max(1, min(limit, 500)), max(0, offset)
        q = text(f"""
            WITH matching_codes AS (
                SELECT DISTINCT ts_code
                FROM {self.schema}.top10_floatholders
                WHERE holder_name = ANY(:holder_names)
                  AND COALESCE(holder_type, '未知') = :holder_type
            ), latest_periods AS (
                SELECT source.ts_code, MAX(source.end_date) AS end_date
                FROM {self.schema}.top10_floatholders source
                JOIN matching_codes matched ON matched.ts_code = source.ts_code
                GROUP BY source.ts_code
            ), positions AS (
                SELECT source.ts_code, source.end_date, MAX(source.ann_date) AS ann_date,
                       ARRAY_AGG(DISTINCT source.holder_name ORDER BY source.holder_name) AS matched_names,
                       SUM(source.hold_amount) AS hold_amount,
                       SUM(source.hold_ratio) AS hold_ratio,
                       SUM(source.hold_float_ratio) AS hold_float_ratio,
                       SUM(source.hold_change) AS hold_change
                FROM {self.schema}.top10_floatholders source
                JOIN latest_periods latest
                  ON latest.ts_code = source.ts_code AND latest.end_date = source.end_date
                WHERE source.holder_name = ANY(:holder_names)
                  AND COALESCE(source.holder_type, '未知') = :holder_type
                GROUP BY source.ts_code, source.end_date
            ), result AS (
                SELECT position.*, stock.name AS company_name, stock.industry, stock.market,
                       COUNT(*) OVER() AS total_count
                FROM positions position
                LEFT JOIN {self.schema}.stock_basic stock ON stock.ts_code = position.ts_code
            )
            SELECT * FROM result
            ORDER BY end_date DESC, ann_date DESC NULLS LAST, ts_code
            LIMIT :limit OFFSET :offset
        """)
        rows = await self._execute_mappings(q, {
            "holder_names": names, "holder_type": holder_type or "未知",
            "limit": limit, "offset": offset,
        })
        total = int(rows[0].get("total_count") or 0) if rows else 0
        for row in rows:
            row.pop("total_count", None)
        cost_estimates: dict[str, dict[str, Any]] = {}
        if rows and await self.table_exists("stock_daily_adj"):
            cost_estimates = await self._holder_current_cost_estimates(
                names, holder_type or "未知", [str(row["ts_code"]) for row in rows],
            )
        for row in rows:
            row["cost_estimate"] = cost_estimates.get(str(row["ts_code"]))
        source_as_of = max((str(row.get("ann_date") or "") for row in rows), default="") or None
        return {"items": rows, "total": total, "source_available": True, "source_as_of": source_as_of}

    async def _holder_current_cost_estimates(
        self,
        holder_names: list[str],
        holder_type: str,
        ts_codes: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Reconstruct the estimable portion of current holdings with an average-cost ledger."""
        if not ts_codes:
            return {}
        q = text(f"""
            WITH company_periods AS (
                SELECT source.ts_code, source.end_date
                FROM {self.schema}.top10_floatholders source
                WHERE source.ts_code = ANY(:ts_codes)
                GROUP BY source.ts_code, source.end_date
            ), positions AS (
                SELECT source.ts_code, source.end_date,
                       SUM(source.hold_amount) AS hold_amount,
                       SUM(source.hold_float_ratio) AS hold_float_ratio,
                       SUM(source.hold_change) AS hold_change
                FROM {self.schema}.top10_floatholders source
                WHERE source.ts_code = ANY(:ts_codes)
                  AND source.holder_name = ANY(:holder_names)
                  AND COALESCE(source.holder_type, '未知') = :holder_type
                GROUP BY source.ts_code, source.end_date
            ), positioned AS (
                SELECT period.ts_code, period.end_date,
                       position.hold_amount, position.hold_float_ratio, position.hold_change,
                       (position.ts_code IS NOT NULL) AS present
                FROM company_periods period
                LEFT JOIN positions position
                  ON position.ts_code = period.ts_code AND position.end_date = period.end_date
            ), timeline AS (
                SELECT positioned.*,
                       LAG(present) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_present,
                       LAG(end_date) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_end_date,
                       LAG(hold_amount) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_hold_amount,
                       LAG(hold_float_ratio) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_hold_float_ratio
                FROM positioned
            ), classified AS (
                SELECT timeline.*,
                       CASE
                           WHEN present AND previous_present IS NULL THEN 'first_seen'
                           WHEN present AND previous_present = false THEN 'new'
                           WHEN NOT present AND previous_present = true THEN 'exited_top10'
                           WHEN present AND previous_present = true AND
                                (hold_amount > previous_hold_amount OR
                                 (hold_amount IS NULL AND hold_float_ratio > previous_hold_float_ratio)) THEN 'increased'
                           WHEN present AND previous_present = true AND
                                (hold_amount < previous_hold_amount OR
                                 (hold_amount IS NULL AND hold_float_ratio < previous_hold_float_ratio)) THEN 'reduced'
                           WHEN present AND previous_present = true THEN 'unchanged'
                           ELSE NULL
                       END AS event_type
                FROM timeline
            )
            SELECT classified.ts_code, classified.end_date, classified.previous_end_date,
                   classified.event_type, classified.hold_amount, classified.previous_hold_amount,
                   classified.hold_change,
                   estimate.estimate_low, estimate.estimate_high,
                   estimate.estimate_volume_weighted_price
            FROM classified
            LEFT JOIN LATERAL (
                SELECT MIN(price.low) AS estimate_low,
                       MAX(price.high) AS estimate_high,
                       SUM(price.close * price.vol) / NULLIF(SUM(price.vol), 0) AS estimate_volume_weighted_price
                FROM {self.schema}.stock_daily_adj price
                WHERE price.ts_code = classified.ts_code
                  AND price.adj_type = 'qfq'
                  AND price.trade_date > TO_DATE(classified.previous_end_date, 'YYYYMMDD')
                  AND price.trade_date <= TO_DATE(classified.end_date, 'YYYYMMDD')
            ) estimate ON classified.previous_end_date IS NOT NULL
              AND classified.event_type IN ('new', 'increased', 'reduced')
            WHERE classified.event_type IS NOT NULL
            ORDER BY classified.ts_code, classified.end_date
        """)
        events = await self._execute_mappings(q, {
            "holder_names": holder_names,
            "holder_type": holder_type,
            "ts_codes": ts_codes,
        })
        return _build_holder_cost_estimates(events)

    async def holder_history(
        self,
        holder_names: list[str],
        holder_type: str,
        *,
        limit: int = 200,
        offset: int = 0,
        min_end_date: str | None = None,
        include_price_estimates: bool = True,
    ) -> dict[str, Any]:
        """Build objective quarter-to-quarter holder events and price-window estimates."""
        if not await self.table_exists("top10_floatholders"):
            return {"items": [], "total": 0, "source_available": False, "source_as_of": None}
        names = [name.strip() for name in holder_names if name.strip()]
        if not names:
            return {"items": [], "total": 0, "source_available": True, "source_as_of": None}
        limit, offset = max(1, min(limit, 1000)), max(0, offset)
        result_filter = "AND classified.end_date >= :min_end_date" if min_end_date else ""
        price_source_available = include_price_estimates and await self.table_exists("stock_daily_adj")
        estimate_join = f"""
            LEFT JOIN LATERAL (
                SELECT MIN(price.low) AS estimate_low,
                       MAX(price.high) AS estimate_high,
                       SUM(price.close * price.vol) / NULLIF(SUM(price.vol), 0) AS estimate_volume_weighted_price,
                       COUNT(*) AS estimate_trading_days,
                       MIN(price.trade_date) AS estimate_first_trade_date,
                       MAX(price.trade_date) AS estimate_last_trade_date
                FROM {self.schema}.stock_daily_adj price
                WHERE price.ts_code = paged.ts_code
                  AND price.adj_type = 'qfq'
                  AND price.trade_date > TO_DATE(paged.previous_end_date, 'YYYYMMDD')
                  AND price.trade_date <= TO_DATE(paged.end_date, 'YYYYMMDD')
            ) estimate ON paged.previous_end_date IS NOT NULL
              AND paged.event_type IN ('new', 'increased', 'reduced', 'exited_top10')
        """ if price_source_available else ""
        estimate_columns = """
                estimate.estimate_low, estimate.estimate_high,
                estimate.estimate_volume_weighted_price, estimate.estimate_trading_days,
                estimate.estimate_first_trade_date, estimate.estimate_last_trade_date
        """ if price_source_available else ""
        q = text(f"""
            WITH matching_codes AS (
                SELECT DISTINCT ts_code
                FROM {self.schema}.top10_floatholders
                WHERE holder_name = ANY(:holder_names)
                  AND COALESCE(holder_type, '未知') = :holder_type
            ), company_periods AS (
                SELECT source.ts_code, source.end_date, MAX(source.ann_date) AS ann_date
                FROM {self.schema}.top10_floatholders source
                JOIN matching_codes matched ON matched.ts_code = source.ts_code
                GROUP BY source.ts_code, source.end_date
            ), positions AS (
                SELECT source.ts_code, source.end_date,
                       ARRAY_AGG(DISTINCT source.holder_name ORDER BY source.holder_name) AS matched_names,
                       SUM(source.hold_amount) AS hold_amount,
                       SUM(source.hold_ratio) AS hold_ratio,
                       SUM(source.hold_float_ratio) AS hold_float_ratio,
                       SUM(source.hold_change) AS hold_change
                FROM {self.schema}.top10_floatholders source
                JOIN matching_codes matched ON matched.ts_code = source.ts_code
                WHERE source.holder_name = ANY(:holder_names)
                  AND COALESCE(source.holder_type, '未知') = :holder_type
                GROUP BY source.ts_code, source.end_date
            ), positioned AS (
                SELECT period.ts_code, period.end_date, period.ann_date,
                       position.matched_names, position.hold_amount, position.hold_ratio,
                       position.hold_float_ratio, position.hold_change,
                       (position.ts_code IS NOT NULL) AS present
                FROM company_periods period
                LEFT JOIN positions position
                  ON position.ts_code = period.ts_code AND position.end_date = period.end_date
            ), timeline AS (
                SELECT positioned.*,
                       LAG(present) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_present,
                       LAG(end_date) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_end_date,
                       LAG(hold_amount) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_hold_amount,
                       LAG(hold_ratio) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_hold_ratio,
                       LAG(hold_float_ratio) OVER (PARTITION BY ts_code ORDER BY end_date) AS previous_hold_float_ratio
                FROM positioned
            ), classified AS (
                SELECT timeline.*,
                       CASE
                           WHEN present AND previous_present IS NULL THEN 'first_seen'
                           WHEN present AND previous_present = false THEN 'new'
                           WHEN NOT present AND previous_present = true THEN 'exited_top10'
                           WHEN present AND previous_present = true AND
                                (hold_amount > previous_hold_amount OR
                                 (hold_amount IS NULL AND hold_float_ratio > previous_hold_float_ratio)) THEN 'increased'
                           WHEN present AND previous_present = true AND
                                (hold_amount < previous_hold_amount OR
                                 (hold_amount IS NULL AND hold_float_ratio < previous_hold_float_ratio)) THEN 'reduced'
                           WHEN present AND previous_present = true THEN 'unchanged'
                           ELSE NULL
                       END AS event_type
                FROM timeline
            ), filtered AS (
                SELECT classified.*, stock.name AS company_name, stock.industry, stock.market,
                       COUNT(*) OVER() AS total_count
                FROM classified
                LEFT JOIN {self.schema}.stock_basic stock ON stock.ts_code = classified.ts_code
                WHERE classified.event_type IS NOT NULL
                  {result_filter}
            ), paged AS (
                SELECT *
                FROM filtered
                ORDER BY end_date DESC, ann_date DESC NULLS LAST, ts_code
                LIMIT :limit OFFSET :offset
            )
            SELECT paged.*{"," if price_source_available else ""}{estimate_columns}
            FROM paged
            {estimate_join}
            ORDER BY paged.end_date DESC, paged.ann_date DESC NULLS LAST, paged.ts_code
        """)
        params: dict[str, Any] = {
            "holder_names": names, "holder_type": holder_type or "未知",
            "limit": limit, "offset": offset,
        }
        if min_end_date:
            params["min_end_date"] = min_end_date
        rows = await self._execute_mappings(q, params)
        total = int(rows[0].get("total_count") or 0) if rows else 0
        for row in rows:
            row.pop("total_count", None)
            event_type = row.get("event_type")
            side = {
                "new": "buy",
                "increased": "buy",
                "reduced": "sell",
                "exited_top10": "possible_sell",
            }.get(event_type)
            low = row.pop("estimate_low", None)
            high = row.pop("estimate_high", None)
            weighted_price = row.pop("estimate_volume_weighted_price", None)
            trading_days = row.pop("estimate_trading_days", None)
            first_trade_date = row.pop("estimate_first_trade_date", None)
            last_trade_date = row.pop("estimate_last_trade_date", None)
            row["price_estimate"] = None
            if side and low is not None and high is not None and weighted_price is not None:
                changed_shares = None
                current_amount = row.get("hold_amount")
                previous_amount = row.get("previous_hold_amount")
                if event_type == "new" and current_amount is not None:
                    changed_shares = current_amount
                elif event_type == "increased" and current_amount is not None and previous_amount is not None:
                    changed_shares = max(0, current_amount - previous_amount)
                elif event_type == "reduced" and current_amount is not None and previous_amount is not None:
                    changed_shares = max(0, previous_amount - current_amount)
                row["price_estimate"] = {
                    "side": side,
                    "window_start": row.get("previous_end_date"),
                    "window_end": row.get("end_date"),
                    "first_trade_date": first_trade_date,
                    "last_trade_date": last_trade_date,
                    "low": low,
                    "high": high,
                    "volume_weighted_price": weighted_price,
                    "trading_days": trading_days,
                    "changed_shares": changed_shares if side != "possible_sell" else None,
                    "estimated_amount": weighted_price * changed_shares
                    if changed_shares is not None and side != "possible_sell" else None,
                    "method": "qfq_close_volume_weighted_reporting_window",
                    "disclaimer": (
                        "按相邻报告期之间的前复权行情估算，并非股东实际成交价。"
                        if side != "possible_sell" else
                        "退出前十仅表示后续榜单未出现，不能确认卖出、卖出数量或已清仓。"
                    ),
                }
        source_as_of = max((str(row.get("ann_date") or "") for row in rows), default="") or None
        return {"items": rows, "total": total, "source_available": True, "source_as_of": source_as_of}

    async def market_capital_snapshot(self, window: int = 60) -> dict[str, Any]:
        """Build one deterministic, source-dated A-share post-close capital snapshot."""
        from services.agent_platform.market_capital import factual_interpretations, pct_change
        window = max(20, min(int(window), 250))
        cached = _market_capital_cache.get(window)
        if cached and time.monotonic() - cached[0] < _MARKET_CAPITAL_CACHE_SECONDS:
            return copy.deepcopy(cached[1])
        if not await self.table_exists("stock_daily"):
            return {"available": False, "as_of": None, "reason": "stock_daily unavailable", "interpretations": []}
        complete = await self._execute_mappings(text(f"""
            WITH daily AS (
              SELECT trade_date, COUNT(*)::int AS row_count FROM {self.schema}.stock_daily
              WHERE trade_date >= (SELECT MAX(trade_date) - INTERVAL '60 days' FROM {self.schema}.stock_daily)
              GROUP BY trade_date ORDER BY trade_date DESC LIMIT 30
            ), baseline AS (
              SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY row_count) AS normal_count FROM daily
            )
            SELECT trade_date,row_count,normal_count FROM daily CROSS JOIN baseline
            WHERE row_count >= normal_count * 0.95 ORDER BY trade_date DESC LIMIT 1
        """), {})
        if not complete:
            return {"available": False, "as_of": None, "reason": "no complete trading day", "interpretations": []}
        as_of = str(complete[0]["trade_date"])
        as_of_date = date.fromisoformat(as_of)
        history = await self._execute_mappings(text(f"""
            SELECT trade_date,COUNT(*)::int AS stock_count,SUM(COALESCE(amount,0))*1000 AS turnover_cny,
                   COUNT(*) FILTER (WHERE pct_chg>0)::int AS advances,
                   COUNT(*) FILTER (WHERE pct_chg<0)::int AS declines,
                   COUNT(*) FILTER (WHERE pct_chg=0)::int AS flat,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY pct_chg) AS median_return_pct
            FROM {self.schema}.stock_daily
            WHERE trade_date IN (
              SELECT trade_date FROM {self.schema}.stock_daily WHERE trade_date<=:as_of
              GROUP BY trade_date ORDER BY trade_date DESC LIMIT :window
            ) GROUP BY trade_date
            ORDER BY trade_date DESC LIMIT :window
        """), {"as_of": as_of_date, "window": window})
        latest = history[0]
        turnovers = [float(row["turnover_cny"] or 0) for row in history]
        avg5 = sum(turnovers[:5]) / len(turnovers[:5])
        avg20 = sum(turnovers[:20]) / len(turnovers[:20])
        concentration = await self._execute_mappings(text(f"""
            WITH ranked AS (
              SELECT amount,ROW_NUMBER() OVER (ORDER BY amount DESC NULLS LAST) AS rank,
                     SUM(COALESCE(amount,0)) OVER () AS total
              FROM {self.schema}.stock_daily WHERE trade_date=:as_of
            ) SELECT SUM(amount) FILTER (WHERE rank<=20)/NULLIF(MAX(total),0) AS top20,
                     SUM(amount) FILTER (WHERE rank<=50)/NULLIF(MAX(total),0) AS top50 FROM ranked
        """), {"as_of": as_of_date})
        liquidity = {"turnover_cny": float(latest["turnover_cny"] or 0), "average_5d_cny": avg5,
                     "average_20d_cny": avg20, "vs_5d_pct": pct_change(float(latest["turnover_cny"] or 0), avg5),
                     "vs_20d_pct": pct_change(float(latest["turnover_cny"] or 0), avg20),
                     "top20_turnover_share": float(concentration[0]["top20"]) if concentration[0]["top20"] is not None else None,
                     "top50_turnover_share": float(concentration[0]["top50"]) if concentration[0]["top50"] is not None else None,
                     "unit": "CNY", "note": "成交额不等于净流入；买卖成交在全市场逐笔匹配。"}
        breadth = {"advances": latest["advances"], "declines": latest["declines"], "flat": latest["flat"],
                   "advance_ratio": latest["advances"] / latest["stock_count"] if latest["stock_count"] else None,
                   "median_return_pct": float(latest["median_return_pct"]) if latest["median_return_pct"] is not None else None,
                   "limit_up": None, "limit_down": None, "limit_source_available": False}
        sources: dict[str, Any] = {"stock_daily": {"available": True, "as_of": as_of, "row_count": complete[0]["row_count"]}}
        if await self.table_exists("stk_limit"):
            limits = await self._execute_mappings(text(f"""
                SELECT COUNT(*) FILTER (WHERE d.close=l.up_limit)::int AS limit_up,
                       COUNT(*) FILTER (WHERE d.close=l.down_limit)::int AS limit_down,COUNT(*)::int AS covered
                FROM {self.schema}.stk_limit l JOIN {self.schema}.stock_daily d
                  ON d.trade_date=l.trade_date AND d.ts_code=l.ts_code WHERE l.trade_date=:as_of
            """), {"as_of": as_of_date})
            if limits and limits[0]["covered"]:
                breadth.update(limit_up=limits[0]["limit_up"], limit_down=limits[0]["limit_down"], limit_source_available=True)
                sources["stk_limit"] = {"available": True, "as_of": as_of, "row_count": limits[0]["covered"]}
            else:
                sources["stk_limit"] = {"available": False, "as_of": None}
        else:
            sources["stk_limit"] = {"available": False, "as_of": None}
        leverage, etfs, rates, proxy = await asyncio.gather(
            self._market_leverage(as_of_date), self._market_etf_flows(as_of_date),
            self._market_funding_rates(as_of_date), self._market_flow_proxy(as_of_date),
        )
        for key, value in (("leverage", leverage), ("etf_flows", etfs), ("shibor", rates), ("moneyflow_mkt_dc", proxy)):
            component_date = value.get("as_of")
            lag_days = (date.fromisoformat(as_of) - date.fromisoformat(component_date)).days if component_date else None
            value["lag_days"] = lag_days
            sources[key] = {"available": bool(value.get("available")), "as_of": component_date, "lag_days": lag_days}
        result = {"available": True, "as_of": as_of, "window": window, "sources": sources,
                  "liquidity": liquidity, "breadth": breadth, "leverage": leverage, "etf_flows": etfs,
                  "funding_rates": rates, "flow_proxy": proxy, "history": list(reversed(history)),
                  "interpretations": [], "methodology": {"scope": "A-share full market",
                  "complete_day_threshold": 0.95, "flow_warning": "成交额不等于净流入"}}
        result["interpretations"] = factual_interpretations(result)
        _market_capital_cache[window] = (time.monotonic(), copy.deepcopy(result))
        return result

    async def _market_leverage(self, as_of: date) -> dict[str, Any]:
        detail_exists, summary_exists = await asyncio.gather(
            self.table_exists("margin_detail"), self.table_exists("margin"),
        )
        if not detail_exists and not summary_exists:
            return {"available": False, "as_of": None, "reason": "financing source unavailable"}
        detail_sql = f"""
            SELECT trade_date,
                   CASE WHEN ts_code LIKE '%.SH' THEN 'SSE' WHEN ts_code LIKE '%.SZ' THEN 'SZSE' ELSE 'OTHER' END AS exchange,
                   SUM(rzye) AS balance,SUM(rzmre) AS purchases,SUM(rzche) AS repayments
            FROM {self.schema}.margin_detail
            WHERE trade_date BETWEEN CAST(:as_of AS date) - INTERVAL '15 days' AND CAST(:as_of AS date)
            GROUP BY trade_date,exchange
        """ if detail_exists else "SELECT NULL::date trade_date,NULL::text exchange,NULL::numeric balance,NULL::numeric purchases,NULL::numeric repayments WHERE false"
        summary_sql = f"""
            SELECT trade_date,exchange_id::text AS exchange,rzye::numeric AS balance,
                   rzmre::numeric AS purchases,rzche::numeric AS repayments
            FROM {self.schema}.margin
            WHERE trade_date BETWEEN CAST(:as_of AS date) - INTERVAL '15 days' AND CAST(:as_of AS date)
        """ if summary_exists else "SELECT NULL::date trade_date,NULL::text exchange,NULL::numeric balance,NULL::numeric purchases,NULL::numeric repayments WHERE false"
        rows = await self._execute_mappings(text(f"""
            WITH detail AS ({detail_sql}), summary AS ({summary_sql}), combined AS (
              SELECT * FROM summary
              UNION ALL
              SELECT detail.* FROM detail
              WHERE NOT EXISTS (
                SELECT 1 FROM summary WHERE summary.trade_date=detail.trade_date AND summary.exchange=detail.exchange
              )
            )
            SELECT trade_date,SUM(balance) AS balance,SUM(purchases) AS purchases,SUM(repayments) AS repayments,
                   ARRAY_AGG(DISTINCT exchange ORDER BY exchange) AS exchanges
            FROM combined GROUP BY trade_date ORDER BY trade_date DESC LIMIT 5
        """), {"as_of": as_of})
        if not rows:
            return {"available": False, "as_of": None, "reason": "no financing rows"}
        latest = rows[0]
        net = lambda row: float(row["purchases"] or 0) - float(row["repayments"] or 0)
        return {"available": True, "as_of": str(latest["trade_date"]), "balance_cny": float(latest["balance"] or 0),
                "purchases_cny": float(latest["purchases"] or 0), "repayments_cny": float(latest["repayments"] or 0),
                "daily_net_financing_cny": net(latest), "five_day_net_financing_cny": sum(net(row) for row in rows),
                "coverage": latest["exchanges"], "coverage_label": "+".join(latest["exchanges"] or []),
                "source_table": "+".join(name for name, exists in (("margin_detail", detail_exists), ("margin", summary_exists)) if exists)}

    async def _market_etf_flows(self, as_of: date) -> dict[str, Any]:
        if not all(await asyncio.gather(
            self.table_exists("fund_basic"), self.table_exists("fund_share"), self.table_exists("fund_nav"),
        )):
            return {"available": False, "as_of": None, "reason": "ETF share or NAV source unavailable"}
        rows = await self._execute_mappings(text(f"""
            WITH etfs AS (
              SELECT ts_code,name,COALESCE(fund_type,'') fund_type,COALESCE(type,'') subtype FROM {self.schema}.fund_basic
              WHERE market='E' AND (name ILIKE '%ETF%' OR type ILIKE '%ETF%' OR fund_type ILIKE '%ETF%')
            )
            SELECT e.*,s.trade_date,s.fd_share,s.previous_share,n.nav_date,n.unit_nav
            FROM etfs e
            JOIN LATERAL (
              SELECT latest.trade_date,latest.fd_share,
                     (SELECT previous.fd_share FROM {self.schema}.fund_share previous
                      WHERE previous.ts_code=e.ts_code AND previous.trade_date<latest.trade_date
                      ORDER BY previous.trade_date DESC LIMIT 1) AS previous_share
              FROM {self.schema}.fund_share latest
              WHERE latest.ts_code=e.ts_code AND latest.trade_date<=:as_of
              ORDER BY latest.trade_date DESC LIMIT 1
            ) s ON true
            LEFT JOIN LATERAL (
              SELECT nav_date,unit_nav FROM {self.schema}.fund_nav n WHERE n.ts_code=e.ts_code AND n.nav_date<=s.trade_date
              ORDER BY nav_date DESC LIMIT 1
            ) n ON true
        """), {"as_of": as_of})
        if not rows:
            return {"available": False, "as_of": None, "reason": "no listed ETF share rows"}
        groups = {key: 0.0 for key in ("equity", "bond", "commodity", "cross_border", "other")}
        covered = 0
        for row in rows:
            label = f"{row.get('name','')} {row.get('fund_type','')} {row.get('subtype','')}"
            category = "cross_border" if any(x in label.upper() for x in ("QDII", "跨境", "纳指", "标普", "恒生", "日经")) else "commodity" if any(x in label for x in ("黄金", "有色", "能源", "商品")) else "bond" if any(x in label for x in ("债", "国债", "信用")) else "equity" if any(x in label for x in ("股票", "指数", "沪深", "中证", "上证", "创业板", "科创")) else "other"
            if row.get("previous_share") is not None and row.get("unit_nav") is not None:
                groups[category] += (float(row["fd_share"] or 0)-float(row["previous_share"]))*10000*float(row["unit_nav"])
                covered += 1
        return {"available": True, "as_of": max(str(row["trade_date"]) for row in rows),
                "estimated_net_flow_cny": sum(groups.values()), "groups": groups, "fund_count": len(rows),
                "flow_covered_funds": covered, "coverage_ratio": covered/len(rows),
                "method": "share_change_x_latest_matching_nav",
                "note": "估算申赎资金流；份额单位按万份换算，净值日期不晚于份额日期。"}

    async def _market_funding_rates(self, as_of: date) -> dict[str, Any]:
        if not await self.table_exists("shibor"):
            return {"available": False, "as_of": None}
        rows = await self._execute_mappings(text(f"SELECT date,\"on\",\"1w\" FROM {self.schema}.shibor WHERE date<=:as_of ORDER BY date DESC LIMIT 2"), {"as_of": as_of})
        if not rows:
            return {"available": False, "as_of": None}
        latest, previous = rows[0], rows[1] if len(rows)>1 else {}
        return {"available": True, "as_of": str(latest["date"]), "overnight_pct": float(latest["on"]) if latest["on"] is not None else None,
                "seven_day_pct": float(latest["1w"]) if latest["1w"] is not None else None,
                "overnight_change_bp": (float(latest["on"])-float(previous["on"]))*100 if previous.get("on") is not None else None,
                "seven_day_change_bp": (float(latest["1w"])-float(previous["1w"]))*100 if previous.get("1w") is not None else None}

    async def _market_flow_proxy(self, as_of: date) -> dict[str, Any]:
        base = {"available": False, "as_of": None, "provider": "Tushare / 东方财富", "separate_proxy": True}
        if not await self.table_exists("moneyflow_mkt_dc"):
            return base
        rows = await self._execute_mappings(text(f"SELECT * FROM {self.schema}.moneyflow_mkt_dc WHERE trade_date<=:as_of ORDER BY trade_date DESC LIMIT 1"), {"as_of": as_of})
        if not rows:
            return base
        row = rows[0]
        return {"available": True, "as_of": str(row.pop("trade_date")), "provider": "Tushare / 东方财富",
                "method": "provider_defined_main_force_proxy", "separate_proxy": True, "values": row,
                "warning": "供应商算法口径，不是全市场逐笔可验证的字面净流入。"}

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


def _build_holder_cost_estimates(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Apply a deterministic average-cost ledger to classified disclosure events."""
    ledgers: dict[str, dict[str, Any]] = {}
    for event in events:
        code = str(event["ts_code"])
        ledger = ledgers.setdefault(code, {
            "known_shares": 0.0, "unknown_shares": 0.0,
            "cost": 0.0, "cost_low": 0.0, "cost_high": 0.0,
            "first_estimated_period": None, "last_estimated_period": None,
        })
        event_type = event.get("event_type")
        current = float(event.get("hold_amount") or 0)
        previous = float(event.get("previous_hold_amount") or 0)
        weighted = event.get("estimate_volume_weighted_price")
        low = event.get("estimate_low")
        high = event.get("estimate_high")

        if event_type == "exited_top10":
            ledger.update(known_shares=0.0, unknown_shares=0.0, cost=0.0, cost_low=0.0, cost_high=0.0)
            ledger["first_estimated_period"] = None
            ledger["last_estimated_period"] = None
            continue
        if event_type == "first_seen":
            ledger.update(known_shares=0.0, unknown_shares=current, cost=0.0, cost_low=0.0, cost_high=0.0)
            ledger["first_estimated_period"] = None
            ledger["last_estimated_period"] = None
            continue
        if event_type == "new":
            ledger.update(known_shares=0.0, unknown_shares=0.0, cost=0.0, cost_low=0.0, cost_high=0.0)
            changed = current
        elif event_type in {"increased", "reduced"}:
            disclosed_change = event.get("hold_change")
            transaction_change = float(disclosed_change) if disclosed_change is not None else current - previous
            corporate_adjusted_base = max(0.0, current - transaction_change)
            scale = corporate_adjusted_base / previous if previous > 0 else 0.0
            ledger["known_shares"] *= scale
            ledger["unknown_shares"] *= scale
            ledger["cost"] *= scale
            ledger["cost_low"] *= scale
            ledger["cost_high"] *= scale
            if transaction_change < 0:
                ratio = min(1.0, current / corporate_adjusted_base) if corporate_adjusted_base > 0 else 0.0
                ledger["known_shares"] *= ratio
                ledger["unknown_shares"] *= ratio
                ledger["cost"] *= ratio
                ledger["cost_low"] *= ratio
                ledger["cost_high"] *= ratio
                continue
            changed = max(0.0, transaction_change)
        else:
            continue

        if changed <= 0:
            continue
        if weighted is None or low is None or high is None:
            ledger["unknown_shares"] += changed
            continue
        ledger["known_shares"] += changed
        ledger["cost"] += changed * float(weighted)
        ledger["cost_low"] += changed * float(low)
        ledger["cost_high"] += changed * float(high)
        ledger["first_estimated_period"] = ledger["first_estimated_period"] or event.get("end_date")
        ledger["last_estimated_period"] = event.get("end_date")

    result: dict[str, dict[str, Any]] = {}
    for code, ledger in ledgers.items():
        known_shares = float(ledger["known_shares"])
        total_shares = known_shares + float(ledger["unknown_shares"])
        if known_shares <= 0 or total_shares <= 0:
            continue
        coverage_ratio = min(1.0, known_shares / total_shares)
        result[code] = {
            "unit_cost": ledger["cost"] / known_shares,
            "unit_cost_low": ledger["cost_low"] / known_shares,
            "unit_cost_high": ledger["cost_high"] / known_shares,
            "covered_shares": known_shares,
            "coverage_ratio": coverage_ratio,
            "estimated_covered_cost": ledger["cost"],
            "estimated_position_cost": ledger["cost"] if coverage_ratio >= 0.999999 else None,
            "first_estimated_period": ledger["first_estimated_period"],
            "last_estimated_period": ledger["last_estimated_period"],
            "method": "qfq_disclosure_average_cost_ledger",
            "disclaimer": (
                "按公开披露的增持价格窗口累计，减持按平均成本比例扣减；"
                "送转股等仅按披露持股数与变动数校正，历史起点前持仓和真实成交无法还原。"
            ),
        }
    return result


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
