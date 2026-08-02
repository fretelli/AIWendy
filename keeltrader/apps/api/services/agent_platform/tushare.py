"""Read-only access to the existing Tushare PostgreSQL schema.

KeelTrader AgentOS never stores or uses a Tushare token. It reads data that
has already been synchronized by an operator-managed Tushare data service.
"""

from __future__ import annotations

import asyncio
import copy
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
import math
import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings
from services.agent_platform.capabilities import physical_tables, queryable_tables


_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

_tushare_session_factory: async_sessionmaker[AsyncSession] | None = None
_tushare_session_url: str | None = None
_market_capital_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_MARKET_CAPITAL_CACHE_SECONDS = 300
_market_domain_cache: dict[str, tuple[float, Any]] = {}
_MARKET_DOMAIN_CACHE_SECONDS = 600


def source_freshness_metadata(
    as_of: date,
    component_date: str | None,
    available: bool,
    trading_dates: set[date] | None = None,
) -> dict[str, Any]:
    """Describe source freshness without presenting lag as a positive change."""
    if not available or not component_date:
        return {
            "available": False,
            "as_of": component_date,
            "lag_days": None,
            "lag_calendar_days": None,
            "lag_trading_days": None,
            "freshness_state": "unavailable",
        }
    try:
        component = date.fromisoformat(str(component_date))
    except ValueError:
        return {
            "available": True,
            "as_of": component_date,
            "lag_days": None,
            "lag_calendar_days": None,
            "lag_trading_days": None,
            "freshness_state": "invalid",
        }
    if component > as_of:
        return {
            "available": True,
            "as_of": str(component),
            "lag_days": None,
            "lag_calendar_days": None,
            "lag_trading_days": None,
            "freshness_state": "invalid",
        }
    calendar_lag = (as_of - component).days
    trading_lag = 0 if calendar_lag == 0 else (
        sum(1 for trading_day in trading_dates if component < trading_day <= as_of)
        if trading_dates is not None else None
    )
    is_current = trading_lag == 0 if trading_lag is not None else calendar_lag == 0
    return {
        "available": True,
        "as_of": str(component),
        "lag_days": calendar_lag,
        "lag_calendar_days": calendar_lag,
        "lag_trading_days": trading_lag,
        "freshness_state": "current" if is_current else "lagged",
    }


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
        if table not in physical_tables():
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

    async def allocation_catalog(self) -> dict[str, Any]:
        """Return allocation data readiness without triggering source ingestion."""
        required_keys = ["cny_cash", "china_equity", "global_equity", "china_bond", "global_bond", "gold"]
        labels = {
            "cny_cash": "人民币流动性", "china_equity": "中国股票", "global_equity": "全球股票",
            "china_bond": "中国债券", "global_bond": "全球债券", "gold": "黄金",
            "broad_commodity": "广义商品",
        }
        if not await self.table_exists("allocation_series_catalog"):
            return {
                "available": False,
                "formal_ready": False,
                "minimum_months": 120,
                "series": [{"sleeve_key": key, "name": labels[key], "required": True,
                            "quality_state": "unavailable", "quality_reason": "资产配置数据目录尚未部署"}
                           for key in required_keys],
                "missing_required": required_keys,
                "methodology": "只接受人民币总回报或直接可投资净值；不使用价格指数、合成曲线或期货拼接代理。",
            }
        rows = await self._execute_mappings(text(f"""
            SELECT series_id,sleeve_key,name,asset_class,currency,return_type,source_name,source_license,
                   underlying_key,required,enabled,quality_state,quality_reason,first_month,last_month,
                   observation_months,unexplained_gap_months,methodology,currency_exposure
            FROM {self.schema}.allocation_series_catalog ORDER BY required DESC,sleeve_key,series_id
        """), {})
        missing = sorted({key for key in required_keys if not any(
            row.get("sleeve_key") == key and row.get("enabled") and row.get("quality_state") == "ready"
            for row in rows
        )})
        return {
            "available": bool(rows), "formal_ready": not missing, "minimum_months": 120,
            "series": rows, "missing_required": missing,
            "methodology": "完整共同月度人民币总回报历史；至少120个月、零无法解释缺口并覆盖最近完整月。",
        }

    async def allocation_monthly(self, series_ids: list[str]) -> list[dict[str, Any]]:
        if not series_ids or not await self.table_exists("allocation_series_monthly"):
            return []
        return await self._execute_mappings(text(f"""
            SELECT series_id,month_end,monthly_return,cny_total_return_index,source_date,content_hash
            FROM {self.schema}.allocation_series_monthly
            WHERE series_id = ANY(:series_ids) AND completeness='complete'
            ORDER BY month_end,series_id
        """), {"series_ids": series_ids})

    async def allocation_series_history(self, series_id: str) -> dict[str, Any]:
        if not await self.table_exists("allocation_series_monthly"):
            return {"series_id": series_id, "points": [], "available": False}
        rows = await self._execute_mappings(text(f"""
            SELECT month_end,monthly_return,cny_total_return_index,source_date,source_ref,content_hash
            FROM {self.schema}.allocation_series_monthly
            WHERE series_id=:series_id AND completeness='complete' ORDER BY month_end
        """), {"series_id": series_id})
        return {"series_id": series_id, "points": rows, "available": bool(rows),
                "full_history": True, "downsampled": False,
                "methodology": "返回数据库当前全部月度人民币总回报物化结果；不生成均线、百分位或代理序列。"}

    async def allocation_instruments(self, sleeve_keys: list[str] | None = None) -> list[dict[str, Any]]:
        if not await self.table_exists("allocation_instrument_catalog"):
            return []
        clauses = "AND sleeve_key = ANY(:sleeve_keys)" if sleeve_keys else ""
        return await self._execute_mappings(text(f"""
            SELECT instrument_id,sleeve_key,instrument_type,code,name,market,currency,underlying_key,
                   source_table,metadata_json
            FROM {self.schema}.allocation_instrument_catalog
            WHERE enabled=true {clauses}
            ORDER BY sleeve_key,instrument_type,code
        """), {"sleeve_keys": sleeve_keys or []})

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

    async def latest_instrument_price(self, instrument_type: str, symbol: str, as_of: date) -> dict[str, Any] | None:
        """Resolve a published price from the official table for one instrument type."""
        specification = {
            "stock": ("stock_daily", "trade_date", "close"),
            "etf": ("fund_daily", "trade_date", "close"),
            "open_fund": ("fund_nav", "nav_date", "unit_nav"),
            "future": ("fut_daily", "trade_date", "settle"),
            "option": ("opt_daily", "trade_date", "settle"),
            "convertible_bond": ("cb_daily", "trade_date", "close"),
        }.get(instrument_type)
        if specification is None:
            return None
        table, date_column, price_column = specification
        if not await self.table_exists(table):
            return None
        rows = await self._execute_mappings(text(f"""
            SELECT {date_column} AS price_as_of,{price_column} AS price
            FROM {self.schema}.{table}
            WHERE ts_code=:symbol AND {date_column}<=:as_of AND {price_column} IS NOT NULL
            ORDER BY {date_column} DESC LIMIT 1
        """), {"symbol": symbol, "as_of": as_of})
        if not rows:
            return None
        return {**rows[0], "source": f"{self.schema}.{table}.{price_column}", "valuation_method": "published_close"}

    async def instrument_price_history(
        self,
        instrument_type: str,
        symbol: str,
        *,
        limit: int = 260,
    ) -> dict[str, Any]:
        """Return the provider-native series used by portfolio valuation.

        The method deliberately mirrors ``latest_instrument_price`` so a
        holdings detail view cannot silently switch to a proxy series.
        """
        specification = {
            "stock": ("stock_daily", "trade_date", "close"),
            "etf": ("fund_daily", "trade_date", "close"),
            "open_fund": ("fund_nav", "nav_date", "unit_nav"),
            "future": ("fut_daily", "trade_date", "settle"),
            "option": ("opt_daily", "trade_date", "settle"),
            "convertible_bond": ("cb_daily", "trade_date", "close"),
        }.get(instrument_type)
        if specification is None:
            return {
                "available": False,
                "instrument_type": instrument_type,
                "symbol": symbol,
                "reason": "provider_series_not_defined",
                "items": [],
            }
        table, date_column, price_column = specification
        if not await self.table_exists(table):
            return {
                "available": False,
                "instrument_type": instrument_type,
                "symbol": symbol,
                "reason": f"{table}_not_published",
                "items": [],
            }
        bounded_limit = max(2, min(limit, 1200))
        rows = await self._execute_mappings(text(f"""
            SELECT {date_column} AS date,{price_column} AS price
            FROM {self.schema}.{table}
            WHERE ts_code=:symbol AND {price_column} IS NOT NULL
            ORDER BY {date_column} DESC LIMIT :limit
        """), {"symbol": symbol, "limit": bounded_limit})
        rows.reverse()
        return {
            "available": bool(rows),
            "instrument_type": instrument_type,
            "symbol": symbol,
            "source": f"{self.schema}.{table}.{price_column}",
            "valuation_method": "published_close",
            "items": rows,
            "reason": None if rows else "published_series_empty",
        }

    async def direct_fx_rate(self, base_currency: str, quote_currency: str, as_of: date) -> dict[str, Any] | None:
        """Return only a provider-native direct FX pair; never synthesize crosses or inverses."""
        base, quote = base_currency.upper(), quote_currency.upper()
        if base == quote:
            return {"rate": 1.0, "fx_as_of": as_of, "source": "identity", "provider_symbol": None}
        if not await self.table_exists("fx_obasic") or not await self.table_exists("fx_daily"):
            return None
        rows = await self._execute_mappings(text(f"""
            SELECT d.ts_code,d.trade_date AS fx_as_of,
                   CASE WHEN d.bid_close IS NOT NULL AND d.ask_close IS NOT NULL
                        THEN (d.bid_close+d.ask_close)/2 ELSE COALESCE(d.bid_close,d.ask_close) END AS rate
            FROM {self.schema}.fx_daily d
            JOIN {self.schema}.fx_obasic b ON b.ts_code=d.ts_code
            WHERE upper(b.base_cur)=:base AND upper(b.quote_cur)=:quote
              AND d.trade_date<=:as_of AND (d.bid_close IS NOT NULL OR d.ask_close IS NOT NULL)
            ORDER BY d.trade_date DESC LIMIT 1
        """), {"base": base, "quote": quote, "as_of": as_of})
        if not rows:
            return None
        return {**rows[0], "source": "tushare.fx_daily.mid", "direct_pair": True}

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

    async def point_in_time_factors(self, symbols: list[str], as_of: date,
                                    prices: dict[str, float]) -> dict[str, dict[str, Any]]:
        """Return only financial facts publicly announced by the requested date."""
        if not symbols or not await self.table_exists("fina_indicator"):
            return {}
        date_key = as_of.strftime("%Y%m%d")
        rows = await self._execute_mappings(text(f"""
            SELECT DISTINCT ON (ts_code) ts_code,end_date,ann_date,roe,ocf_to_or,tr_yoy,netprofit_yoy
            FROM {self.schema}.fina_indicator
            WHERE ts_code=ANY(:symbols) AND ann_date IS NOT NULL AND ann_date<=:as_of
            ORDER BY ts_code,end_date DESC,ann_date DESC
        """), {"symbols": symbols, "as_of": date_key})
        dividends = []
        if await self.table_exists("dividend"):
            dividends = await self._execute_mappings(text(f"""
                SELECT ts_code,SUM(COALESCE(cash_div,0)) AS trailing_cash_dividend
                FROM {self.schema}.dividend
                WHERE ts_code=ANY(:symbols) AND ann_date<=:as_of
                  AND ann_date>=:start_date AND div_proc ILIKE '%%实施%%'
                GROUP BY ts_code
            """), {"symbols": symbols, "as_of": date_key,
                    "start_date": date(as_of.year - 1, as_of.month, min(as_of.day, 28)).strftime("%Y%m%d")})
        dividend_map = {row["ts_code"]: float(row.get("trailing_cash_dividend") or 0) for row in dividends}
        result = {}
        for row in rows:
            symbol = str(row["ts_code"])
            price = prices.get(symbol)
            result[symbol] = {
                "as_of": as_of.isoformat(), "report_end_date": row.get("end_date"), "announcement_date": row.get("ann_date"),
                "roe": row.get("roe"), "cash_quality": row.get("ocf_to_or"),
                "revenue_growth": row.get("tr_yoy"), "profit_growth": row.get("netprofit_yoy"),
                "dividend_yield": dividend_map.get(symbol, 0) / price if price and price > 0 else None,
                "source": f"{self.schema}.fina_indicator+dividend", "point_in_time": True,
            }
        return result

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
        # ann_date and end_date are indexed in the managed Tushare schema.
        # Aggregating the unindexed update timestamp forces a full history scan
        # and can exceed the read-only statement timeout as the table grows.
        q = text(
            f"SELECT MAX(ann_date) AS ann_date, MAX(end_date) AS end_date "
            f"FROM {self.schema}.top10_floatholders"
        )
        async with self._session_scope() as session:
            row = (await session.execute(q)).mappings().one()
        ann_date = _json_safe(row.get("ann_date"))
        end_date = _json_safe(row.get("end_date"))
        return f"{ann_date or ''}|{end_date or ''}" if ann_date or end_date else None

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

    async def market_capital_snapshot(self) -> dict[str, Any]:
        """Build one deterministic, source-dated A-share post-close capital snapshot."""
        from services.agent_platform.market_capital import factual_interpretations
        cache_key = "all_raw_history"
        cached = _market_capital_cache.get(cache_key)
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
              SELECT MAX(row_count) AS normal_count FROM daily
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
                   COUNT(*) FILTER (WHERE pct_chg=0)::int AS flat
            FROM {self.schema}.stock_daily
            WHERE trade_date<=:as_of
            GROUP BY trade_date
            ORDER BY trade_date ASC
        """), {"as_of": as_of_date})
        latest = history[-1]
        concentration = await self._execute_mappings(text(f"""
            WITH ranked AS (
              SELECT amount,ROW_NUMBER() OVER (ORDER BY amount DESC NULLS LAST) AS rank,
                     SUM(COALESCE(amount,0)) OVER () AS total
              FROM {self.schema}.stock_daily WHERE trade_date=:as_of
            ) SELECT SUM(amount) FILTER (WHERE rank<=20)/NULLIF(MAX(total),0) AS top20,
                     SUM(amount) FILTER (WHERE rank<=50)/NULLIF(MAX(total),0) AS top50 FROM ranked
        """), {"as_of": as_of_date})
        liquidity = {"turnover_cny": float(latest["turnover_cny"] or 0),
                     "top20_turnover_share": float(concentration[0]["top20"]) if concentration[0]["top20"] is not None else None,
                     "top50_turnover_share": float(concentration[0]["top50"]) if concentration[0]["top50"] is not None else None,
                     "unit": "CNY", "note": "成交额不等于净流入；买卖成交在全市场逐笔匹配。"}
        breadth = {"advances": latest["advances"], "declines": latest["declines"], "flat": latest["flat"],
                   "advance_ratio": latest["advances"] / latest["stock_count"] if latest["stock_count"] else None,
                   "limit_up": None, "limit_down": None, "limit_source_available": False}
        sources: dict[str, Any] = {"stock_daily": {
            **source_freshness_metadata(as_of_date, as_of, True, {as_of_date}),
            "row_count": complete[0]["row_count"],
        }}
        if await self.table_exists("stk_limit"):
            limits = await self._execute_mappings(text(f"""
                SELECT COUNT(*) FILTER (WHERE d.close=l.up_limit)::int AS limit_up,
                       COUNT(*) FILTER (WHERE d.close=l.down_limit)::int AS limit_down,COUNT(*)::int AS covered
                FROM {self.schema}.stk_limit l JOIN {self.schema}.stock_daily d
                  ON d.trade_date=l.trade_date AND d.ts_code=l.ts_code WHERE l.trade_date=:as_of
            """), {"as_of": as_of_date})
            if limits and limits[0]["covered"]:
                breadth.update(limit_up=limits[0]["limit_up"], limit_down=limits[0]["limit_down"], limit_source_available=True)
                sources["stk_limit"] = {
                    **source_freshness_metadata(as_of_date, as_of, True, {as_of_date}),
                    "row_count": limits[0]["covered"],
                }
            else:
                sources["stk_limit"] = source_freshness_metadata(as_of_date, None, False)
        else:
            sources["stk_limit"] = source_freshness_metadata(as_of_date, None, False)
        leverage, etfs, rates, proxy = await asyncio.gather(
            self._market_leverage(as_of_date), self._market_etf_flows(as_of_date),
            self._market_funding_rates(as_of_date), self._market_flow_proxy(as_of_date),
        )
        component_values = (("leverage", leverage), ("etf_flows", etfs), ("shibor", rates), ("moneyflow_mkt_dc", proxy))
        component_dates = []
        for _, value in component_values:
            try:
                if value.get("as_of"):
                    component_dates.append(date.fromisoformat(str(value["as_of"])))
            except ValueError:
                continue
        trading_dates: set[date] | None = None
        if component_dates and await self.table_exists("trade_cal"):
            rows = await self._execute_mappings(text(f"""
                SELECT cal_date FROM {self.schema}.trade_cal
                WHERE exchange='SSE' AND is_open=1 AND cal_date>:start_date AND cal_date<=:as_of
            """), {"start_date": min(component_dates), "as_of": as_of_date})
            parsed_trading_dates = {
                date.fromisoformat(str(row["cal_date"])) for row in rows if row.get("cal_date")
            }
            trading_dates = parsed_trading_dates or None
        for key, value in component_values:
            freshness = source_freshness_metadata(
                as_of_date, value.get("as_of"), bool(value.get("available")), trading_dates,
            )
            value.update(freshness)
            sources[key] = freshness.copy()
        result = {"available": True, "as_of": as_of, "window": "all", "sources": sources,
                  "liquidity": liquidity, "breadth": breadth, "leverage": leverage, "etf_flows": etfs,
                  "funding_rates": rates, "flow_proxy": proxy, "history": history,
                  "history_meta": {"scope": "all_available", "raw": True,
                  "start_date": str(history[0]["trade_date"]), "end_date": str(history[-1]["trade_date"]),
                  "points": len(history), "source": f"{self.schema}.stock_daily"},
                  "interpretations": [], "methodology": {"scope": "A-share full market",
                  "complete_day_threshold": 0.95, "flow_warning": "成交额不等于净流入"}}
        result["interpretations"] = factual_interpretations(result)
        _market_capital_cache[cache_key] = (time.monotonic(), copy.deepcopy(result))
        return result

    async def macro_market_snapshot(self) -> dict[str, Any]:
        """Return every synchronized raw macro series without normalization or scoring."""
        cache_key = "macro_market"
        cached = _market_domain_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < _MARKET_DOMAIN_CACHE_SECONDS:
            return copy.deepcopy(cached[1])
        definitions = {
            "gdp": ("cn_gdp", "quarter", "quarterly"),
            "cpi": ("cn_cpi", "month", "monthly"),
            "ppi": ("cn_ppi", "month", "monthly"),
            "money_supply": ("cn_m", "month", "monthly"),
            "social_financing": ("sf_month", "month", "monthly"),
            "pmi": ("cn_pmi", "month", "monthly"),
            "shibor": ("shibor", "date", "daily"),
            "lpr": ("lpr", "date", "monthly"),
            "us_treasury": ("us_tycr", "date", "daily"),
            "us_real_treasury": ("us_trycr", "date", "daily"),
        }
        series: dict[str, Any] = {}
        for key, (table, period_column, frequency) in definitions.items():
            if not await self.table_exists(table):
                series[key] = {"available": False, "table": table, "frequency": frequency, "rows": []}
                continue
            rows = await self._execute_mappings(text(
                f"SELECT * FROM {self.schema}.{table} ORDER BY {period_column} ASC"
            ), {})
            series[key] = {
                "available": bool(rows), "table": table, "frequency": frequency,
                "period_field": period_column, "start": str(rows[0].get(period_column)) if rows else None,
                "end": str(rows[-1].get(period_column)) if rows else None,
                "points": len(rows), "raw": True, "rows": rows,
            }
        result = {"available": any(value["available"] for value in series.values()), "series": series,
                  "methodology": {"raw": True, "local_transforms": False,
                  "note": "同比与环比仅在上游源字段存在时原样展示。"}}
        _market_domain_cache[cache_key] = (time.monotonic(), copy.deepcopy(result))
        return result

    @staticmethod
    def macro_definitions() -> dict[str, tuple[str, str, str, str]]:
        return {
            "gdp": ("cn_gdp", "quarter", "quarterly", "国内生产总值"),
            "cpi": ("cn_cpi", "month", "monthly", "居民消费价格"),
            "ppi": ("cn_ppi", "month", "monthly", "工业生产者价格"),
            "money_supply": ("cn_m", "month", "monthly", "货币供应"),
            "social_financing": ("sf_month", "month", "monthly", "社会融资"),
            "pmi": ("cn_pmi", "month", "monthly", "采购经理指数"),
            "shibor": ("shibor", "date", "daily", "上海银行间拆放利率"),
            "lpr": ("lpr", "date", "monthly", "贷款市场报价利率"),
            "us_treasury": ("us_tycr", "date", "daily", "美国国债收益率"),
            "us_real_treasury": ("us_trycr", "date", "daily", "美国实际国债收益率"),
        }

    async def macro_catalog(self) -> dict[str, Any]:
        """Return metadata only; never download every macro row for navigation."""
        async def describe(key: str, definition: tuple[str, str, str, str]) -> dict[str, Any]:
            table, period, frequency, label = definition
            if not await self.table_exists(table):
                return {"key": key, "label": label, "table": table, "available": False, "fields": []}
            columns = await self._execute_mappings(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema=:schema AND table_name=:table
                ORDER BY ordinal_position
            """), {"schema": self.schema, "table": table})
            numeric_types = {"smallint", "integer", "bigint", "numeric", "real", "double precision"}
            fields = [row["column_name"] for row in columns if row["data_type"] in numeric_types]
            stats = await self._execute_mappings(text(
                f"SELECT MIN({period}) AS start, MAX({period}) AS end, COUNT(*)::int AS points FROM {self.schema}.{table}"
            ), {})
            meta = stats[0] if stats else {}
            return {"key": key, "label": label, "table": table, "frequency": frequency,
                    "period_field": period, "available": bool(meta.get("points")), "fields": fields,
                    "start": str(meta.get("start")) if meta.get("start") else None,
                    "end": str(meta.get("end")) if meta.get("end") else None,
                    "points": int(meta.get("points") or 0), "source": f"{self.schema}.{table}"}
        items = await asyncio.gather(*(describe(key, value) for key, value in self.macro_definitions().items()))
        return {"available": any(item["available"] for item in items), "items": items,
                "methodology": {"raw": True, "local_transforms": False}}

    async def macro_series(self, key: str, field: str) -> dict[str, Any]:
        definition = self.macro_definitions().get(key)
        if not definition:
            raise ValueError("Unknown macro series")
        table, period, frequency, label = definition
        catalog = await self.macro_catalog()
        meta = next(item for item in catalog["items"] if item["key"] == key)
        if field not in meta["fields"]:
            raise ValueError("Unknown macro source field")
        rows, recent = await asyncio.gather(
            self._execute_mappings(text(
                f'SELECT {period} AS period, "{field}" AS value FROM {self.schema}.{table} ORDER BY {period} ASC'
            ), {}),
            self._execute_mappings(text(
                f"SELECT * FROM {self.schema}.{table} ORDER BY {period} DESC LIMIT 12"
            ), {}),
        )
        return {"available": bool(rows), "key": key, "label": label, "field": field,
                "frequency": frequency, "period_field": period, "source": f"{self.schema}.{table}",
                "start": str(rows[0]["period"]) if rows else None,
                "end": str(rows[-1]["period"]) if rows else None, "points": len(rows),
                "raw": True, "rows": rows, "recent_source_rows": recent}

    @staticmethod
    def rates_definitions() -> dict[str, tuple[str, str, str, str]]:
        return {
            "shibor": ("shibor", "date", "daily", "SHIBOR"),
            "shibor_quotes": ("shibor_quote", "date", "daily", "SHIBOR 报价行"),
            "lpr": ("lpr", "date", "monthly", "LPR"),
            "repo": ("repo_daily", "trade_date", "daily", "银行间质押式回购"),
            "us_nominal": ("us_tycr", "date", "daily", "美国国债名义收益率"),
            "us_real": ("us_trycr", "date", "daily", "美国国债实际收益率"),
        }

    async def rates_catalog(self) -> dict[str, Any]:
        items = []
        for key, (table, period, frequency, label) in self.rates_definitions().items():
            if not await self.table_exists(table):
                items.append({"key": key, "label": label, "table": table, "available": False, "fields": []})
                continue
            columns = await self._execute_mappings(text("""SELECT column_name,data_type FROM information_schema.columns
                WHERE table_schema=:schema AND table_name=:table ORDER BY ordinal_position"""),
                {"schema": self.schema, "table": table})
            numeric = {"smallint", "integer", "bigint", "numeric", "real", "double precision"}
            fields = [row["column_name"] for row in columns if row["data_type"] in numeric]
            stats = await self._execute_mappings(text(f"SELECT MIN({period}) start,MAX({period}) end,COUNT(*)::int points FROM {self.schema}.{table}"), {})
            meta = stats[0] if stats else {}
            items.append({"key": key, "label": label, "table": table, "frequency": frequency,
                          "period_field": period, "available": bool(meta.get("points")), "fields": fields,
                          "start": str(meta.get("start")) if meta.get("start") else None,
                          "end": str(meta.get("end")) if meta.get("end") else None,
                          "points": int(meta.get("points") or 0), "source": f"{self.schema}.{table}"})
        items.append({"key": "china_cash_treasury_curve", "label": "中国现券国债收益率曲线", "table": None,
                      "available": False, "fields": [], "unavailable_reason": "当前数据源未接入 yc_cb；不使用国债期货或其他价格伪造现券收益率曲线。"})
        return {"available": any(item["available"] for item in items), "items": items,
                "methodology": {"raw_history": True, "synthetic_prices": False}}

    async def rates_series(self, key: str, field: str, bank: str | None = None,
                           maturity: str | None = None) -> dict[str, Any]:
        definition = self.rates_definitions().get(key)
        if not definition: raise ValueError("Unknown rates series")
        table, period, frequency, label = definition
        catalog = await self.rates_catalog(); meta = next(item for item in catalog["items"] if item["key"] == key)
        if field not in meta["fields"]: raise ValueError("Unknown rates source field")
        filters, params = [], {}
        if table == "shibor_quote" and bank: filters.append("bank=:bank"); params["bank"] = bank
        if table == "repo_daily" and maturity: filters.append("repo_maturity=:maturity"); params["maturity"] = maturity
        where = " WHERE " + " AND ".join(filters) if filters else ""
        dimensions = ",bank" if table == "shibor_quote" else (",repo_maturity" if table == "repo_daily" else "")
        rows = await self._execute_mappings(text(f'SELECT {period} AS period,"{field}" AS value{dimensions} FROM {self.schema}.{table}{where} ORDER BY {period} ASC'), params)
        return {"available": bool(rows), "key": key, "label": label, "field": field, "frequency": frequency,
                "period_field": period, "source": f"{self.schema}.{table}", "start": str(rows[0]["period"]) if rows else None,
                "end": str(rows[-1]["period"]) if rows else None, "points": len(rows), "raw": True, "rows": rows}

    async def rates_curve(self, key: str, curve_date: date | None = None) -> dict[str, Any]:
        definitions = {"shibor": ("shibor", "date"), "us_nominal": ("us_tycr", "date"), "us_real": ("us_trycr", "date")}
        if key == "china_cash_treasury":
            return {"available": False, "key": key, "unavailable_reason": "中国现券国债收益率曲线未接入；不进行替代推算。", "points": []}
        if key not in definitions: raise ValueError("Unknown curve")
        table, period = definitions[key]; chosen = curve_date
        if chosen is None:
            latest = await self._execute_mappings(text(f"SELECT MAX({period}) value FROM {self.schema}.{table}"), {})
            chosen = latest[0].get("value") if latest else None
        if isinstance(chosen, str):
            chosen = date.fromisoformat(chosen)
        row = await self._execute_mappings(text(f"SELECT * FROM {self.schema}.{table} WHERE {period}=:chosen LIMIT 1"), {"chosen": chosen}) if chosen else []
        points = [{"tenor": k, "value": v} for k, v in (row[0].items() if row else []) if k not in {period,"created_at","updated_at"} and v is not None]
        return {"available": bool(points), "key": key, "date": str(chosen) if chosen else None,
                "source": f"{self.schema}.{table}", "raw": True, "points": points}

    async def treasury_futures(self) -> dict[str, Any]:
        products = await self.futures_products()
        items = [item for item in products.get("items", []) if str(item.get("fut_code") or item.get("product_code") or "").upper().split(".")[0] in {"T","TF","TS","TL"}]
        return {"available": bool(items), "items": items, "source": products.get("source"), "raw": True,
                "methodology": "国债期货对应可交割国债篮子，不代表单一现券收益率。"}

    async def convertibles(self, code: str | None = None, limit: int = 200, offset: int = 0) -> dict[str, Any]:
        if not all([await self.table_exists("cb_basic"), await self.table_exists("cb_daily")]):
            return {"available": False, "items": [], "total": 0}
        params = {"limit": max(1, min(limit, 500)), "offset": max(0, offset)}
        where = ""
        if code:
            params["code"] = code
            where = "WHERE b.ts_code=:code OR b.stk_code=:code"
        rows = await self._execute_mappings(text(f"""WITH latest AS (SELECT DISTINCT ON(ts_code) * FROM {self.schema}.cb_daily ORDER BY ts_code,trade_date DESC)
            SELECT b.*,d.trade_date,d.close,d.vol,d.amount,d.bond_value,d.bond_over_rate,d.cb_value,d.cb_over_rate,
            COUNT(*) OVER()::int total FROM {self.schema}.cb_basic b LEFT JOIN latest d ON d.ts_code=b.ts_code
            {where} ORDER BY d.trade_date DESC NULLS LAST,b.ts_code
            LIMIT :limit OFFSET :offset"""), params)
        total = int(rows[0].get("total") or 0) if rows else 0
        for row in rows: row.pop("total", None)
        return {"available": bool(rows), "items": rows, "total": total, "limit": params["limit"], "offset": params["offset"],
                "source": f"{self.schema}.cb_basic+cb_daily", "raw": True}

    async def futures_products(self) -> dict[str, Any]:
        cached = _market_domain_cache.get("futures_products")
        if cached and time.monotonic() - cached[0] < _MARKET_DOMAIN_CACHE_SECONDS:
            return copy.deepcopy(cached[1])
        if not all([await self.table_exists("fut_mapping"), await self.table_exists("fut_daily")]):
            return {"available": False, "items": []}
        rows = await self._execute_mappings(text(f"""
            WITH latest AS (
              SELECT DISTINCT ON (m.ts_code) m.ts_code AS product_code,m.trade_date,m.mapping_ts_code
              FROM {self.schema}.fut_mapping m
              ORDER BY m.ts_code,m.trade_date DESC
            )
            SELECT l.product_code,l.trade_date,l.mapping_ts_code,b.name,b.fut_code,b.exchange,
                   d.close,d.settle,d.vol,d.amount,d.oi
            FROM latest l
            JOIN {self.schema}.fut_daily d ON d.ts_code=l.mapping_ts_code AND d.trade_date=l.trade_date
            LEFT JOIN {self.schema}.fut_basic b ON b.ts_code=l.mapping_ts_code
            ORDER BY COALESCE(b.exchange,''),l.product_code
        """), {})
        result = {"available": bool(rows), "as_of": max((str(row["trade_date"]) for row in rows), default=None),
                  "items": rows, "source": "tushare.fut_mapping+fut_daily+fut_basic", "raw": True}
        _market_domain_cache["futures_products"] = (time.monotonic(), copy.deepcopy(result))
        return result

    async def futures_history(self, product_code: str) -> dict[str, Any]:
        rows = await self._execute_mappings(text(f"""
            SELECT m.trade_date,m.ts_code AS product_code,m.mapping_ts_code AS contract_code,
                   d.open,d.high,d.low,d.close,d.settle,d.vol,d.amount,d.oi,d.oi_chg
            FROM {self.schema}.fut_mapping m
            JOIN {self.schema}.fut_daily d ON d.ts_code=m.mapping_ts_code AND d.trade_date=m.trade_date
            WHERE m.ts_code=:product_code
            ORDER BY m.trade_date ASC
        """), {"product_code": product_code})
        return {"available": bool(rows), "product_code": product_code, "history": rows,
                "history_meta": {"scope": "all_available", "raw": True,
                "start_date": str(rows[0]["trade_date"]) if rows else None,
                "end_date": str(rows[-1]["trade_date"]) if rows else None, "points": len(rows),
                "adjusted": False, "source": "tushare.fut_mapping+fut_daily"}}

    async def futures_curve(self, product_code: str, trade_date: date | None = None) -> dict[str, Any]:
        roots = await self._execute_mappings(text(f"""
            SELECT b.fut_code FROM {self.schema}.fut_mapping m
            JOIN {self.schema}.fut_basic b ON b.ts_code=m.mapping_ts_code
            WHERE m.ts_code=:product_code ORDER BY m.trade_date DESC LIMIT 1
        """), {"product_code": product_code})
        fut_code = roots[0]["fut_code"] if roots else None
        chosen = trade_date
        if chosen is None and fut_code:
            latest = await self._execute_mappings(text(f"""
                SELECT MAX(d.trade_date) AS trade_date FROM {self.schema}.fut_daily d
                JOIN {self.schema}.fut_basic b ON b.ts_code=d.ts_code WHERE b.fut_code=:fut_code
            """), {"fut_code": fut_code})
            chosen = latest[0]["trade_date"] if latest and latest[0].get("trade_date") else None
        if isinstance(chosen, str):
            chosen = date.fromisoformat(chosen)
        rows = [] if chosen is None or not fut_code else await self._execute_mappings(text(f"""
            SELECT d.trade_date,d.ts_code AS contract_code,b.name,b.list_date,b.delist_date,
                   d.close,d.settle,d.vol,d.amount,d.oi
            FROM {self.schema}.fut_daily d JOIN {self.schema}.fut_basic b ON b.ts_code=d.ts_code
            WHERE b.fut_code=:fut_code AND d.trade_date=:trade_date
            ORDER BY b.delist_date ASC NULLS LAST,d.ts_code
        """), {"fut_code": fut_code, "trade_date": chosen})
        return {"available": bool(rows), "product_code": product_code,
                "fut_code": fut_code, "trade_date": str(chosen) if chosen else None, "items": rows, "raw": True}

    async def options_series(self) -> dict[str, Any]:
        cached = _market_domain_cache.get("options_series")
        if cached and time.monotonic() - cached[0] < _MARKET_DOMAIN_CACHE_SECONDS:
            return copy.deepcopy(cached[1])
        if not await self.table_exists("opt_basic"):
            return {"available": False, "items": []}
        rows = await self._execute_mappings(text(f"""
            SELECT opt_code,exchange,MAX(opt_type) AS opt_type,MIN(list_date) AS list_date,
                   MAX(maturity_date) AS latest_maturity,COUNT(*)::int AS contracts,
                   COUNT(*) FILTER (WHERE delist_date IS NULL OR delist_date>=CURRENT_DATE)::int AS active_contracts,
                   CASE
                     WHEN opt_code IN ('IO','OP000300.SH') THEN '000300.SH'
                     WHEN opt_code IN ('HO','OP000016.SH') THEN '000016.SH'
                     WHEN opt_code IN ('MO','OP000852.SH') THEN '000852.SH'
                     WHEN opt_code LIKE 'OP510050.SH%' THEN '510050.SH'
                     WHEN opt_code LIKE 'OP510300.SH%' THEN '510300.SH'
                     WHEN opt_code LIKE 'OP510500.SH%' THEN '510500.SH'
                     WHEN opt_code LIKE 'OP588000.SH%' THEN '588000.SH'
                     WHEN opt_code LIKE 'OP588080.SH%' THEN '588080.SH'
                     WHEN opt_code LIKE 'OP159901.SZ%' THEN '159901.SZ'
                     WHEN opt_code LIKE 'OP159915.SZ%' THEN '159915.SZ'
                     WHEN opt_code LIKE 'OP159919.SZ%' THEN '159919.SZ'
                     WHEN opt_code LIKE 'OP159922.SZ%' THEN '159922.SZ'
                     WHEN opt_code LIKE 'OP%.%' THEN SUBSTRING(opt_code FROM 3)
                     ELSE NULL
                   END AS underlying_code,
                   CASE WHEN opt_code IN ('IO','HO','MO','OP000300.SH','OP000016.SH','OP000852.SH') THEN 'index'
                     WHEN opt_code LIKE 'OP510%.SH%' OR opt_code LIKE 'OP588%.SH%'
                       OR opt_code LIKE 'OP159%.SZ%' THEN 'etf'
                     WHEN opt_code LIKE 'OP%.%' THEN 'futures_contract' ELSE 'unresolved' END AS underlying_type
            FROM {self.schema}.opt_basic WHERE opt_code IS NOT NULL
            GROUP BY opt_code,exchange ORDER BY exchange,opt_code
        """), {})
        watermark = await self._execute_mappings(text(f"SELECT MIN(trade_date) start_date,MAX(trade_date) end_date FROM {self.schema}.opt_daily"), {})
        result = {"available": bool(rows), "items": rows, "history_meta": {
                  "scope": "current_available", "raw": True,
                  "start_date": str(watermark[0]["start_date"]) if watermark and watermark[0]["start_date"] else None,
                  "end_date": str(watermark[0]["end_date"]) if watermark and watermark[0]["end_date"] else None,
                  "backfill_target": "2015-02-09", "source": "tushare.opt_basic+opt_daily"}}
        _market_domain_cache["options_series"] = (time.monotonic(), copy.deepcopy(result))
        return result

    async def options_history(self, opt_code: str) -> dict[str, Any]:
        rows = await self._execute_mappings(text(f"""
            SELECT trade_date,call_vol AS call_volume,put_vol AS put_volume,
                   call_amount,put_amount,total_amount,call_oi,put_oi,
                   call_contract_count AS call_contracts,put_contract_count AS put_contracts
            FROM {self.schema}.opt_series_daily
            WHERE opt_code=:opt_code ORDER BY trade_date ASC
        """), {"opt_code": opt_code})
        return {"available": bool(rows), "opt_code": opt_code, "history": rows,
                "history_meta": {"scope": "current_available", "raw_aggregation": True,
                "start_date": str(rows[0]["trade_date"]) if rows else None,
                "end_date": str(rows[-1]["trade_date"]) if rows else None,
                "points": len(rows), "source": "tushare.opt_series_daily (from opt_daily+opt_basic)"}}

    async def futures_underlying(self, product_code: str) -> dict[str, Any]:
        index_map = {
            "IF": ("000300.SH", "沪深300指数"), "IH": ("000016.SH", "上证50指数"),
            "IC": ("000905.SH", "中证500指数"), "IM": ("000852.SH", "中证1000指数"),
        }
        root = product_code.upper().removesuffix(".CFX")
        if root in index_map:
            code, name = index_map[root]
            return await self._underlying_payload("index", code, name, "index_daily")
        if root in {"T", "TF", "TS", "TL"}:
            return {"available": True, "relationship": "deliverable_bond_basket", "code": None,
                    "name": "可交割国债篮子", "series_available": False,
                    "methodology": "国债期货对应可交割券篮子，不伪造单一现货价格。"}
        return {"available": True, "relationship": "commodity_physical_market", "code": None,
                "name": "商品现货市场", "series_available": False,
                "methodology": "商品期货没有唯一且可通用的现货序列；仅展示交易所合约与主力映射。"}

    async def option_underlying(self, opt_code: str) -> dict[str, Any]:
        financial = {
            "IO": ("index", "000300.SH", "沪深300指数", "index_daily"),
            "HO": ("index", "000016.SH", "上证50指数", "index_daily"),
            "MO": ("index", "000852.SH", "中证1000指数", "index_daily"),
            "OP000300.SH": ("index", "000300.SH", "沪深300指数", "index_daily"),
            "OP000016.SH": ("index", "000016.SH", "上证50指数", "index_daily"),
            "OP000852.SH": ("index", "000852.SH", "中证1000指数", "index_daily"),
            "OP510050.SH": ("etf", "510050.SH", "50ETF", "fund_daily"),
            "OP510300.SH": ("etf", "510300.SH", "300ETF", "fund_daily"),
            "OP510500.SH": ("etf", "510500.SH", "500ETF", "fund_daily"),
            "OP588000.SH": ("etf", "588000.SH", "科创50ETF", "fund_daily"),
            "OP588080.SH": ("etf", "588080.SH", "科创板50ETF", "fund_daily"),
            "OP159901.SZ": ("etf", "159901.SZ", "深100ETF", "fund_daily"),
            "OP159915.SZ": ("etf", "159915.SZ", "创业板ETF", "fund_daily"),
            "OP159919.SZ": ("etf", "159919.SZ", "沪深300ETF", "fund_daily"),
            "OP159922.SZ": ("etf", "159922.SZ", "中证500ETF", "fund_daily"),
        }
        key = opt_code.upper()
        if key in financial:
            kind, code, name, table = financial[key]
            return await self._underlying_payload(kind, code, name, table)
        if key in {"IO", "HO", "MO"}:
            kind, code, name, table = financial[key]
            return await self._underlying_payload(kind, code, name, table)
        if key.startswith("OP") and "." in key:
            contract_code = key[2:]
            rows = await self._execute_mappings(text(f"""
                SELECT ts_code,name,exchange,list_date,delist_date,per_unit,quote_unit,quote_unit_desc
                FROM {self.schema}.fut_basic WHERE ts_code=:code LIMIT 1
            """), {"code": contract_code})
            return {"available": bool(rows), "relationship": "futures_contract", "code": contract_code,
                    "name": rows[0].get("name") if rows else contract_code, "source": f"{self.schema}.fut_basic+fut_daily",
                    "series_available": await self.table_exists("fut_daily"), "specification": rows[0] if rows else None,
                    "methodology": "期货期权序列代码按交易所规则精确对应同交易所期货合约。"}
        return {"available": False, "relationship": "unresolved", "code": None,
                "series_available": False, "methodology": "源合约无可核验的底层标的映射。"}

    async def _underlying_payload(self, kind: str, code: str, name: str, table: str) -> dict[str, Any]:
        return {"available": True, "relationship": kind, "code": code, "name": name,
                "source": f"{self.schema}.{table}", "series_available": await self.table_exists(table),
                "methodology": "交易所产品与标准化底层标的的明确对应关系。"}

    async def underlying_series(self, relationship: str, code: str) -> dict[str, Any]:
        table = {"index": "index_daily", "etf": "fund_daily", "futures_contract": "fut_daily"}.get(relationship)
        if not table or not await self.table_exists(table):
            return {"available": False, "relationship": relationship, "code": code, "rows": []}
        rows = await self._execute_mappings(text(f"""
            SELECT trade_date,open,high,low,close,pre_close,vol,amount
            FROM {self.schema}.{table} WHERE ts_code=:code ORDER BY trade_date ASC
        """), {"code": code})
        return {"available": bool(rows), "relationship": relationship, "code": code, "raw": True,
                "source": f"{self.schema}.{table}", "start": str(rows[0]["trade_date"]) if rows else None,
                "end": str(rows[-1]["trade_date"]) if rows else None, "points": len(rows), "rows": rows}

    async def options_chain(self, opt_code: str, trade_date: date | None = None,
                            maturity: date | None = None, limit: int = 300, offset: int = 0) -> dict[str, Any]:
        limit, offset = max(1, min(limit, 500)), max(0, offset)
        chosen = trade_date
        if chosen is None:
            latest = await self._execute_mappings(text(f"""
                SELECT MAX(trade_date) AS trade_date FROM {self.schema}.opt_series_daily
                WHERE opt_code=:opt_code
            """), {"opt_code": opt_code})
            chosen = latest[0]["trade_date"] if latest and latest[0].get("trade_date") else None
        if isinstance(chosen, str):
            chosen = date.fromisoformat(chosen)
        params = {"opt_code": opt_code, "trade_date": chosen, "maturity": maturity,
                  "limit": limit, "offset": offset}
        fallback_ctes = ""
        fallback_union = ""
        if opt_code.upper().endswith(".ZCE"):
            fallback_ctes = f""",
            missing_scope AS MATERIALIZED (
                SELECT d.trade_date,d.ts_code,d.open,d.high,d.low,d.close,d.settle,d.vol,d.amount,d.oi,
                       regexp_replace(d.ts_code, '[CP][0-9]+[.]ZCE$', '') AS contract_root
                FROM {self.schema}.opt_daily d
                LEFT JOIN {self.schema}.opt_basic exact ON exact.ts_code=d.ts_code
                WHERE d.trade_date=CAST(:trade_date AS date) AND exact.ts_code IS NULL
                  AND d.ts_code ~ '^[A-Z]+[0-9]+[CP][0-9]+[.]ZCE$'
            ), candidate_series AS MATERIALIZED (
                SELECT roots.contract_root,MIN(candidate.opt_code) AS opt_code,
                       MIN(candidate.exchange) AS exchange,
                       MIN(candidate.maturity_date) AS maturity_date
                FROM (SELECT DISTINCT contract_root FROM missing_scope) roots
                JOIN {self.schema}.opt_basic candidate
                  ON regexp_replace(candidate.ts_code, '[CP][0-9]+[.]ZCE$', '')=roots.contract_root
                WHERE candidate.exchange='ZCE'
                GROUP BY roots.contract_root
                HAVING COUNT(DISTINCT candidate.opt_code)=1
                   AND COUNT(DISTINCT candidate.maturity_date)=1
            )"""
            fallback_union = """
                UNION ALL
                SELECT d.trade_date,d.ts_code,NULL::text AS name,sibling.exchange,
                       CASE WHEN d.ts_code ~ 'C[0-9]+[.]ZCE$' THEN 'C'
                            WHEN d.ts_code ~ 'P[0-9]+[.]ZCE$' THEN 'P' END AS call_put,
                       substring(d.ts_code FROM '[CP]([0-9]+)[.]ZCE$')::numeric AS exercise_price,
                       sibling.maturity_date,d.open,d.high,d.low,d.close,d.settle,d.vol,d.amount,d.oi
                FROM missing_scope d
                JOIN candidate_series sibling ON sibling.contract_root=d.contract_root
                WHERE sibling.opt_code=:opt_code
            """
        rows = [] if chosen is None else await self._execute_mappings(text(f"""
            WITH exact_scope AS MATERIALIZED (
                SELECT d.trade_date,d.ts_code,b.name,b.exchange,b.call_put,b.exercise_price,b.maturity_date,
                       d.open,d.high,d.low,d.close,d.settle,d.vol,d.amount,d.oi
                FROM {self.schema}.opt_basic b
                JOIN {self.schema}.opt_daily d ON d.ts_code=b.ts_code
                WHERE b.opt_code=:opt_code AND d.trade_date=CAST(:trade_date AS date)
            ){fallback_ctes}, resolved_scope AS (
                SELECT * FROM exact_scope
                {fallback_union}
            )
            SELECT trade_date,ts_code,name,exchange,call_put,exercise_price,maturity_date,
                   open,high,low,close,settle,vol,amount,oi,
                   COUNT(*) OVER()::int AS total
            FROM resolved_scope
            WHERE (CAST(:maturity AS date) IS NULL OR maturity_date=CAST(:maturity AS date))
            ORDER BY maturity_date,exercise_price,call_put LIMIT :limit OFFSET :offset
        """), params)
        total = rows[0].get("total", 0) if rows else 0
        for row in rows:
            row.pop("total", None)
        return {"available": bool(rows), "opt_code": opt_code, "trade_date": str(chosen) if chosen else None,
                "maturity": str(maturity) if maturity else None, "items": rows, "total": total,
                "limit": limit, "offset": offset, "raw": True}

    async def options_surface(self, opt_code: str, trade_date: date | None = None) -> dict[str, Any]:
        if not await self.table_exists("option_analytics_daily"):
            return {"available": False, "opt_code": opt_code, "items": [], "reason": "analytics table unavailable"}
        chosen = trade_date
        if chosen is None:
            latest = await self._execute_mappings(text(f"SELECT MAX(trade_date) value FROM {self.schema}.option_analytics_daily WHERE opt_code=:code"), {"code": opt_code})
            chosen = latest[0].get("value") if latest else None
        if isinstance(chosen, str):
            chosen = date.fromisoformat(chosen)
        rows = await self._execute_mappings(text(f"""SELECT a.trade_date,a.ts_code,b.call_put,b.exercise_price,b.maturity_date,
            a.implied_volatility,a.delta,a.gamma,a.theta,a.vega,a.rho,a.convergence_status,a.unavailable_reason,
            a.model_family,a.model_version,a.option_price_field,a.risk_free_rate,a.underlying_price
            FROM {self.schema}.option_analytics_daily a JOIN {self.schema}.opt_basic b ON b.ts_code=a.ts_code
            WHERE a.opt_code=:code AND a.trade_date=:chosen ORDER BY b.maturity_date,b.exercise_price,b.call_put"""),
            {"code": opt_code, "chosen": chosen}) if chosen else []
        return {"available": bool(rows), "opt_code": opt_code, "trade_date": str(chosen) if chosen else None,
                "items": rows, "source": f"{self.schema}.option_analytics_daily",
                "methodology": {"interpolation": False, "raw_contract_points": True}}

    async def options_exposures(self, opt_code: str, trade_date: date | None = None) -> dict[str, Any]:
        if not await self.table_exists("option_analytics_daily"):
            return {"available": False, "opt_code": opt_code, "items": [], "reason": "analytics table unavailable"}
        chosen = trade_date
        if chosen is None:
            latest = await self._execute_mappings(text(f"SELECT MAX(trade_date) value FROM {self.schema}.option_analytics_daily WHERE opt_code=:code"), {"code": opt_code})
            chosen = latest[0].get("value") if latest else None
        if isinstance(chosen, str):
            chosen = date.fromisoformat(chosen)
        rows = await self._execute_mappings(text(f"""SELECT b.maturity_date,b.call_put,
            SUM(a.gross_oi_delta) gross_oi_delta,SUM(a.gross_oi_gamma) gross_oi_gamma,SUM(a.gross_oi_vega) gross_oi_vega,
            SUM(a.oi) gross_open_interest,COUNT(*) FILTER(WHERE a.convergence_status='converged')::int resolved_contracts,
            COUNT(*)::int contracts FROM {self.schema}.option_analytics_daily a JOIN {self.schema}.opt_basic b ON b.ts_code=a.ts_code
            WHERE a.opt_code=:code AND a.trade_date=:chosen GROUP BY b.maturity_date,b.call_put ORDER BY b.maturity_date,b.call_put"""),
            {"code": opt_code, "chosen": chosen}) if chosen else []
        return {"available": bool(rows), "opt_code": opt_code, "trade_date": str(chosen) if chosen else None,
                "items": rows, "source": f"{self.schema}.option_analytics_daily",
                "methodology": "gross OI-weighted sensitivity; not dealer net positioning"}

    def _option_contract_resolution_cte(self, restrict_to_trade_date: bool = False) -> str:
        """Resolve source-lagged CZCE contracts only when one official sibling series exists."""
        date_filter = "AND daily.trade_date=CAST(:trade_date AS date)" if restrict_to_trade_date else ""
        return f"""
            resolved_option_contracts AS (
                SELECT ts_code,opt_code,exchange,name,underlying,call_put,
                       exercise_price,maturity_date
                FROM {self.schema}.opt_basic
                WHERE opt_code IS NOT NULL AND opt_code <> ''
                UNION ALL
                SELECT
                    missing.ts_code,
                    sibling.opt_code,
                    sibling.exchange,
                    NULL::text AS name,
                    sibling.underlying,
                    CASE
                        WHEN missing.ts_code ~ 'C[0-9]+[.]ZCE$' THEN 'C'
                        WHEN missing.ts_code ~ 'P[0-9]+[.]ZCE$' THEN 'P'
                    END AS call_put,
                    substring(missing.ts_code FROM '[CP]([0-9]+)[.]ZCE$')::numeric,
                    sibling.maturity_date
                FROM (
                    SELECT DISTINCT daily.ts_code
                    FROM {self.schema}.opt_daily daily
                    LEFT JOIN {self.schema}.opt_basic exact ON exact.ts_code=daily.ts_code
                    WHERE exact.ts_code IS NULL
                      {date_filter}
                      AND daily.ts_code ~ '^[A-Z]+[0-9]+[CP][0-9]+[.]ZCE$'
                ) missing
                JOIN LATERAL (
                    SELECT MIN(candidate.opt_code) AS opt_code,
                           MIN(candidate.exchange) AS exchange,
                           MIN(candidate.underlying) AS underlying,
                           MIN(candidate.maturity_date) AS maturity_date
                    FROM {self.schema}.opt_basic candidate
                    WHERE regexp_replace(candidate.ts_code, '[CP][0-9]+[.]ZCE$', '') =
                          regexp_replace(missing.ts_code, '[CP][0-9]+[.]ZCE$', '')
                    HAVING COUNT(DISTINCT candidate.opt_code)=1
                       AND COUNT(DISTINCT candidate.maturity_date)=1
                ) sibling ON sibling.opt_code IS NOT NULL
            )
        """

    async def _market_leverage(self, as_of: date) -> dict[str, Any]:
        detail_exists, summary_exists = await asyncio.gather(
            self.table_exists("margin_detail"), self.table_exists("margin"),
        )
        if not detail_exists and not summary_exists:
            return {"available": False, "as_of": None, "reason": "financing source unavailable"}
        detail_sql = f"""
            SELECT trade_date,
                   CASE
                     WHEN ts_code LIKE '%.SH' THEN 'SSE'
                     WHEN ts_code LIKE '%.SZ' THEN 'SZSE'
                     WHEN ts_code LIKE '%.BJ' THEN 'BSE'
                     ELSE 'OTHER'
                   END AS exchange,
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
        if table not in queryable_tables():
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
        converted = float(value)
        return converted if math.isfinite(converted) else None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value
