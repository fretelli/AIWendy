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
    "top10_floatholders",
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
        total = int(rows[0].pop("total_count")) if rows else 0
        source_as_of = max((str(row.get("ann_date") or "") for row in rows), default="") or None
        return {"items": rows, "total": total, "source_available": True, "source_as_of": source_as_of}

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
