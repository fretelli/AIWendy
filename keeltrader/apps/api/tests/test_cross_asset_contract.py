from pathlib import Path
from datetime import date

import pytest

from services.agent_platform.tushare import TushareReadService


ROOT = Path(__file__).resolve().parents[1]


def test_cross_asset_routes_and_human_only_execution_contract():
    markets = (ROOT / "routers/markets.py").read_text()
    opportunities = (ROOT / "services/agent_platform/opportunities.py").read_text()
    assert '"/rates/catalog"' in markets
    assert '"/bonds/convertibles"' in markets
    assert '"/options/{code}/surface"' in markets
    assert '"/options/{code}/exposures"' in markets
    assert '"/opportunities/{opportunity_id}/trade-plan"' in markets
    assert "human_confirmation_required=True" in opportunities
    assert "fixed_risk" in opportunities
    assert "kelly" not in opportunities.lower()
    assert "place_order" not in opportunities


def test_china_cash_treasury_gap_is_explicit_not_synthetic():
    source = (ROOT / "services/agent_platform/tushare.py").read_text()
    assert "中国现券国债收益率曲线未接入" in source
    assert "不进行替代推算" in source
    assert "gross OI-weighted sensitivity; not dealer net positioning" in source


@pytest.mark.asyncio
async def test_latest_market_dates_are_bound_as_native_dates():
    reader = TushareReadService(None)

    async def table_exists(_table: str) -> bool:
        return True

    reader.table_exists = table_exists  # type: ignore[method-assign]

    async def rates_execute(query, params):
        sql = str(query)
        if "MAX(date)" in sql:
            return [{"value": "2026-07-21"}]
        assert isinstance(params["chosen"], date)
        return [{"date": "2026-07-21", "on": 1.2}]

    reader._execute_mappings = rates_execute  # type: ignore[method-assign]
    curve = await reader.rates_curve("shibor")
    assert curve["date"] == "2026-07-21"

    for method_name in ("options_surface", "options_exposures"):
        async def option_execute(query, params):
            sql = str(query)
            if "MAX(trade_date)" in sql:
                return [{"value": "2026-07-21"}]
            assert isinstance(params["chosen"], date)
            return []

        reader._execute_mappings = option_execute  # type: ignore[method-assign]
        result = await getattr(reader, method_name)("OP000016.SH")
        assert result["trade_date"] == "2026-07-21"


@pytest.mark.asyncio
async def test_convertible_filter_does_not_bind_an_untyped_null():
    reader = TushareReadService(None)
    queries: list[tuple[str, dict]] = []

    async def table_exists(_table: str) -> bool:
        return True

    async def execute(query, params):
        queries.append((str(query), params))
        return []

    reader.table_exists = table_exists  # type: ignore[method-assign]
    reader._execute_mappings = execute  # type: ignore[method-assign]

    await reader.convertibles()
    sql, params = queries[-1]
    assert ":code IS NULL" not in sql
    assert "code" not in params

    await reader.convertibles("110000.SH")
    sql, params = queries[-1]
    assert "b.ts_code=:code OR b.stk_code=:code" in sql
    assert params["code"] == "110000.SH"
