"""AgentOS research and brief workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from fastapi import HTTPException

from domain.agentos.models import InvestmentBrief, InvestmentMemo
from services.agentos.report_kb import ReportKBService
from services.agentos.tushare_read import TushareReadService


def _as_iso(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class AgentOSResearchService:
    """Research-oriented AgentOS workflows."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tushare = TushareReadService(session)
        self.reports = ReportKBService()

    async def _search_reports(
        self,
        user_id: UUID,
        query: str,
        *,
        top_k: int,
        companies: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        local_hits = await self.reports.search_reports(
            query,
            top_k=top_k,
            companies=companies,
        )
        cloud_hits: list[dict[str, Any]] = []
        try:
            from routers.research_cloud import _get_connection, _mcp_call

            connection = await _get_connection(self.session, user_id)
            if connection and connection.status == "active" and connection.cloud_auto_context:
                payload = await _mcp_call(
                    self.session,
                    user_id,
                    "search_reports",
                    {
                        "query": query[:500],
                        "top_k": top_k,
                        "companies": [str(item)[:100] for item in (companies or [])[:10]],
                    },
                )
                for item in payload.get("results", []) if isinstance(payload, dict) else []:
                    if not isinstance(item, dict):
                        continue
                    cloud_hits.append({
                        "report_id": str(item.get("report_id") or ""),
                        "section_id": "",
                        "title": item.get("title"),
                        "broker": item.get("broker"),
                        "report_date": item.get("report_date"),
                        "created_at": None,
                        "doc_type": "research_report",
                        "section_type": None,
                        "granularity": "cloud_summary",
                        "page_number": None,
                        "score": 0,
                        "excerpt": str(item.get("summary") or "")[:1000],
                        "metadata": {
                            "source": "research_cloud",
                            "summary_points": item.get("summary_points") or [],
                            "tags": item.get("tags") or [],
                        },
                    })
        except (HTTPException, httpx.HTTPError):
            cloud_hits = []

        merged: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for item in [*local_hits, *cloud_hits]:
            key = (str(item.get("report_id") or ""), str(item.get("title") or ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= top_k:
                break
        return merged

    async def run_daily_brief(
        self,
        user_id: UUID,
        watchlist: list[str] | None = None,
        project_id: UUID | None = None,
    ) -> InvestmentBrief:
        """Generate a deterministic v1 daily brief from available structured data."""
        watchlist = watchlist or []
        signals = []
        risks = []
        falsifiers = []
        missing_data = []

        for symbol in watchlist[:20]:
            profile = await self.tushare.stock_profile(symbol)
            bars = await self.tushare.daily_bars(symbol, limit=30, adjusted=False)
            if profile is None and not bars:
                missing_data.append(symbol)
            latest = bars[0] if bars else {}
            prev = bars[1] if len(bars) > 1 else {}
            close = latest.get("close")
            prev_close = prev.get("close")
            pct = None
            if close is not None and prev_close:
                pct = round((float(close) - float(prev_close)) / float(prev_close) * 100, 2)
            financials = await self.tushare.financial_indicators(symbol, limit=2)
            report_query = " ".join(
                item
                for item in [
                    profile.get("name") if profile else None,
                    profile.get("industry") if profile else None,
                    symbol,
                ]
                if item
            )
            report_hits = await self._search_reports(
                user_id,
                report_query or symbol,
                top_k=3,
                companies=[profile.get("name")] if profile and profile.get("name") else None,
            )

            signals.append({
                "symbol": symbol,
                "name": profile.get("name") if profile else None,
                "latest_trade_date": _as_iso(latest.get("trade_date")) if latest else None,
                "close": close,
                "change_pct": pct,
                "research_priority": "fundamental_review",
                "data_quality": {
                    "has_profile": profile is not None,
                    "has_recent_price": bool(latest),
                    "has_financials": bool(financials),
                    "report_count": len(report_hits),
                },
                "report_count": len(report_hits),
                "latest_report_date": report_hits[0].get("report_date") if report_hits else None,
                "top_report_titles": [hit.get("title") for hit in report_hits[:3] if hit.get("title")],
                "reports": report_hits,
            })
            falsifiers.append({
                "symbol": symbol,
                "condition": "If fundamentals, disclosures, or source timestamps contradict the thesis, require a fresh memo before acting.",
            })

        risks.append("This brief is research support only; it is not an instruction to trade.")
        risks.append("Tushare data may lag upstream publication; confirm timestamps before decisions.")
        if missing_data:
            risks.append(
                "No synchronized Tushare profile/bar data was found for: "
                + ", ".join(missing_data[:10])
            )

        brief = InvestmentBrief(
            user_id=user_id,
            project_id=project_id,
            title=f"AgentOS Daily Brief {datetime.utcnow().date().isoformat()}",
            watchlist=watchlist,
            summary=(
                f"Generated {len(signals)} fundamental research item(s). "
                "Use this brief to prioritize research and record decisions before trading."
            ),
            signals=signals,
            risks=risks,
            falsifiers=falsifiers,
            data_sources=["postgres:tushare", "report-kb:search", "keeltrader:decision-journal"],
            status="published",
        )
        self.session.add(brief)
        await self.session.flush()
        return brief

    async def latest_brief(self, user_id: UUID) -> InvestmentBrief | None:
        result = await self.session.execute(
            select(InvestmentBrief)
            .where(InvestmentBrief.user_id == user_id)
            .order_by(desc(InvestmentBrief.brief_date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def run_deep_research(
        self,
        user_id: UUID,
        symbol: str,
        market: str | None = None,
        project_id: UUID | None = None,
    ) -> InvestmentMemo:
        """Create a structured memo skeleton from Tushare data."""
        profile = await self.tushare.stock_profile(symbol)
        bars = await self.tushare.daily_bars(symbol, limit=30, adjusted=False)
        financials = await self.tushare.financial_indicators(symbol, limit=4)
        data_gaps = []
        if profile is None:
            data_gaps.append("stock_basic")
        if not bars:
            data_gaps.append("stock_daily")
        if not financials:
            data_gaps.append("fina_indicator")

        latest = bars[0] if bars else {}
        name = profile.get("name") if profile else symbol
        report_query = " ".join(
            item
            for item in [
                name,
                profile.get("industry") if profile else None,
                symbol,
                "投资 研报 盈利 风险",
            ]
            if item
        )
        report_hits = await self._search_reports(
            user_id,
            report_query,
            top_k=8,
            companies=[name] if name and name != symbol else None,
        )
        analyst_views = {
            "company_profile": profile or {},
            "financials": {
                "profile": profile,
                "recent_financial_indicators": financials[:4],
                "view": "Review recent profitability, growth, leverage, and cash flow before any decision.",
            },
            "valuation_context": {
                "latest_price_record": latest,
                "view": "Price is retained only as valuation context; no chart signal is generated.",
            },
            "data_quality": {
                "data_gaps": data_gaps,
                "view": "Require source-date checks and fresh filings/reports before any investment decision.",
            },
            "research_reports": {
                "query": report_query,
                "count": len(report_hits),
                "reports": report_hits,
                "view": "Use these report-kb hits as cited research context, not as a trading instruction.",
            },
        }

        memo = InvestmentMemo(
            user_id=user_id,
            project_id=project_id,
            symbol=symbol,
            market=market or "cn_equity",
            title=f"{name} ({symbol}) AgentOS Research Memo",
            thesis="No trade should be placed from this memo alone; use it to structure fundamental bull/bear/risk review.",
            analyst_views=analyst_views,
            bull_case="Bull case requires improving fundamentals, durable cash generation, credible management execution, and reasonable valuation.",
            bear_case="Bear case includes data lag, deteriorating fundamentals, valuation risk, weak governance, and macro/sector pressure.",
            red_team="Invalidate the thesis if key facts are stale, source timestamps are after the decision point, or the setup depends on one fragile assumption.",
            risk_view=(
                "Keep sizing conservative, predefine stop/invalidation, and log the final human decision."
                + (f" Data gaps: {', '.join(data_gaps)}." if data_gaps else "")
            ),
            recommendation="research_only",
            confidence=0.0,
            falsifiers=[
                "New information contradicts the core thesis.",
                "Valuation no longer offers an adequate margin of safety.",
                "Financial data is stale or restated.",
            ],
            data_sources=[
                "postgres:tushare.stock_basic" + (" (missing)" if "stock_basic" in data_gaps else ""),
                "postgres:tushare.stock_daily" + (" (missing)" if "stock_daily" in data_gaps else ""),
                "postgres:tushare.fina_indicator" + (" (missing)" if "fina_indicator" in data_gaps else ""),
                "report-kb:search" + (" (empty)" if not report_hits else ""),
            ],
            status="published",
        )
        self.session.add(memo)
        await self.session.flush()
        return memo

    async def search_reports(
        self,
        user_id: UUID,
        query: str,
        top_k: int = 5,
        companies: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return await self._search_reports(
            user_id,
            query,
            top_k=top_k,
            companies=companies,
        )

    async def get_memo(self, user_id: UUID, memo_id: UUID) -> InvestmentMemo | None:
        result = await self.session.execute(
            select(InvestmentMemo).where(InvestmentMemo.id == memo_id, InvestmentMemo.user_id == user_id)
        )
        return result.scalar_one_or_none()
