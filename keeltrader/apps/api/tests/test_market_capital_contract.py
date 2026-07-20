from pathlib import Path

from services.agent_platform.market_capital import etf_flow, factual_interpretations, financing_net, market_day

ROOT = Path(__file__).resolve().parents[3]


def test_market_formulas_are_explicit_and_unit_safe():
    result = market_day([{"amount": 10, "pct_chg": 2}, {"amount": 5, "pct_chg": -1}, {"amount": 1, "pct_chg": 0}])
    assert result["turnover_cny"] == 16_000
    assert (result["advances"], result["declines"], result["flat"]) == (1, 1, 1)
    assert "median_return_pct" not in result
    assert result["top20_turnover_share"] == 1
    assert financing_net(120, 70) == 50
    assert etf_flow(110, 100, 1.2) == 120_000


def test_missing_proxy_is_not_converted_to_zero():
    lines = factual_interpretations({"liquidity": {}, "breadth": {}, "flow_proxy": {"available": False}})
    assert "不可用" in lines[0] and "未使用成交额替代" in lines[0]


def test_endpoint_and_tool_contracts_are_exposed():
    router = (ROOT / "apps/api/routers/agent_platform.py").read_text()
    tools = (ROOT / "apps/api/services/agent_platform/tools.py").read_text()
    assert '@router.get("/market-capital")' in router
    assert '"market_capital_snapshot"' in tools


def test_market_capital_uses_all_raw_history_without_average_indicators():
    service = (ROOT / "apps/api/services/agent_platform/tushare.py").read_text()
    router = (ROOT / "apps/api/routers/agent_platform.py").read_text()
    facts = (ROOT / "apps/api/services/agent_platform/market_capital.py").read_text()
    assert '"scope": "all_available"' in service
    assert '"raw": True' in service
    assert 'ORDER BY trade_date ASC' in service
    assert "LIMIT :window" not in service
    assert "average_20d_cny" not in service
    assert "vs_20d_pct" not in service
    assert "window: int = Query" not in router
    assert "20日均值" not in facts
    assert "percentile_cont" not in service
    assert "median_return_pct" not in service


def test_margin_detail_maps_beijing_exchange_before_summary_deduplication():
    service = (ROOT / "apps/api/services/agent_platform/tushare.py").read_text()
    assert "WHEN ts_code LIKE '%.BJ' THEN 'BSE'" in service
