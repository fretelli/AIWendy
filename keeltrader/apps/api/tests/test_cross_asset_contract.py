from pathlib import Path


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
