"""AgentOS research and brief workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

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
            report_query = " ".join(
                item
                for item in [
                    profile.get("name") if profile else None,
                    profile.get("industry") if profile else None,
                    symbol,
                ]
                if item
            )
            report_hits = await self.reports.search_reports(
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
                "signal": (
                    "watch"
                    if pct is None
                    else "momentum_up"
                    if pct > 3
                    else "momentum_down"
                    if pct < -3
                    else "neutral"
                ),
                "report_count": len(report_hits),
                "latest_report_date": report_hits[0].get("report_date") if report_hits else None,
                "top_report_titles": [hit.get("title") for hit in report_hits[:3] if hit.get("title")],
                "reports": report_hits,
            })
            falsifiers.append({
                "symbol": symbol,
                "condition": "If price action or fundamentals contradict the thesis, require a fresh memo before acting.",
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
                f"Generated {len(signals)} watchlist signal(s). "
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
        bars = await self.tushare.daily_bars(symbol, limit=120, adjusted=False)
        indicators = await self.tushare.financial_indicators(symbol, limit=4)
        data_gaps = []
        if profile is None:
            data_gaps.append("stock_basic")
        if not bars:
            data_gaps.append("stock_daily")
        if not indicators:
            data_gaps.append("fina_indicator")

        latest = bars[0] if bars else {}
        closes = [float(row["close"]) for row in bars if row.get("close") is not None]
        ma20 = round(sum(closes[:20]) / 20, 4) if len(closes) >= 20 else None
        current = float(latest["close"]) if latest.get("close") is not None else None
        trend = "unknown"
        if current is not None and ma20 is not None:
            trend = "above_20d_average" if current > ma20 else "below_20d_average"

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
        report_hits = await self.reports.search_reports(
            report_query,
            top_k=8,
            companies=[name] if name and name != symbol else None,
        )
        analyst_views = {
            "fundamental": {
                "profile": profile,
                "recent_financial_indicators": indicators[:2],
                "view": "Review recent profitability, growth, leverage, and cash flow before any decision.",
            },
            "technical": {
                "latest_bar": latest,
                "ma20": ma20,
                "trend": trend,
            },
            "quant": {
                "sample_size": len(bars),
                "note": "v1 memo uses deterministic descriptive stats only; no alpha claim is made.",
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
            thesis="No trade should be placed from this memo alone; use it to structure bull/bear/risk review.",
            analyst_views=analyst_views,
            bull_case="Bull case requires improving fundamentals, confirmed liquidity, and price confirmation.",
            bear_case="Bear case includes data lag, weak trend, valuation risk, and macro/sector pressure.",
            red_team="Invalidate the thesis if key facts are stale, source timestamps are after the decision point, or the setup depends on one fragile indicator.",
            risk_view=(
                "Keep sizing conservative, predefine stop/invalidation, and log the final human decision."
                + (f" Data gaps: {', '.join(data_gaps)}." if data_gaps else "")
            ),
            recommendation="research_only",
            confidence=0.0,
            falsifiers=[
                "New information contradicts the core thesis.",
                "Price breaks the predefined invalidation level.",
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
        query: str,
        top_k: int = 5,
        companies: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return await self.reports.search_reports(query, top_k=top_k, companies=companies)

    async def get_memo(self, user_id: UUID, memo_id: UUID) -> InvestmentMemo | None:
        result = await self.session.execute(
            select(InvestmentMemo).where(InvestmentMemo.id == memo_id, InvestmentMemo.user_id == user_id)
        )
        return result.scalar_one_or_none()
