from pathlib import Path
from decimal import Decimal
from datetime import date

from services.agent_platform.market_capital import etf_flow, factual_interpretations, financing_net, market_day
from services.agent_platform.tushare import _json_safe, source_freshness_metadata

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


def test_source_freshness_distinguishes_trading_and_calendar_lag():
    metadata = source_freshness_metadata(
        date(2026, 7, 20), "2026-07-17", True, {date(2026, 7, 20)},
    )
    assert metadata["lag_days"] == 3
    assert metadata["lag_calendar_days"] == 3
    assert metadata["lag_trading_days"] == 1
    assert metadata["freshness_state"] == "lagged"


def test_source_freshness_rejects_future_dates_and_marks_unavailable():
    assert source_freshness_metadata(date(2026, 7, 20), "2026-07-21", True)["freshness_state"] == "invalid"
    assert source_freshness_metadata(date(2026, 7, 20), None, False)["freshness_state"] == "unavailable"


def test_source_freshness_uses_trading_lag_for_current_state_when_available():
    metadata = source_freshness_metadata(date(2026, 7, 20), "2026-07-19", True, set())
    assert metadata["lag_calendar_days"] == 1
    assert metadata["lag_trading_days"] == 0
    assert metadata["freshness_state"] == "current"
    same_day = source_freshness_metadata(date(2026, 7, 20), "2026-07-20", True)
    assert same_day["lag_trading_days"] == 0


def test_macro_futures_and_options_routes_keep_raw_source_contracts():
    service = (ROOT / "apps/api/services/agent_platform/tushare.py").read_text()
    router = (ROOT / "apps/api/routers/agent_platform.py").read_text()
    markets_router = (ROOT / "apps/api/routers/markets.py").read_text()
    for route in (
        '/macro-market', '/futures/products', '/futures/{product_code}/history',
        '/futures/{product_code}/curve', '/options/series',
        '/options/{opt_code}/history', '/options/{opt_code}/chain',
    ):
        assert f'@router.get("{route}")' in router
    assert '"local_transforms": False' in service
    assert '"adjusted": False' in service
    assert 'WHERE m.ts_code=:product_code ORDER BY m.trade_date DESC LIMIT 1' in service
    assert service.count('chosen = date.fromisoformat(chosen)') >= 2
    assert 'CAST(:maturity AS date)' in service
    assert '"scope": "current_available"' in service
    assert 'ORDER BY m.trade_date ASC' in service
    assert 'FROM {self.schema}.opt_series_daily' in service
    assert 'WHERE opt_code=:opt_code ORDER BY trade_date ASC' in service
    assert 'WITH exact_scope AS MATERIALIZED' in service
    assert 'missing_scope AS MATERIALIZED' in service
    assert 'candidate_series AS MATERIALIZED' in service
    assert 'SELECT DISTINCT contract_root FROM missing_scope' in service
    assert 'if opt_code.upper().endswith(".ZCE")' in service
    assert 'FROM {self.schema}.opt_series_daily' in service
    assert 'WHERE opt_code=:opt_code' in service
    assert 'HAVING COUNT(DISTINCT candidate.opt_code)=1' in service
    assert 'trade_date=CAST(:trade_date AS date)' in service
    assert '"OP000300.SH": ("index", "000300.SH"' in service
    assert '"OP000016.SH": ("index", "000016.SH"' in service
    assert '"OP000852.SH": ("index", "000852.SH"' in service
    assert '@router.get("/macro/series/{key}")' in markets_router
    assert '@router.get("/options/{code}/underlying")' in markets_router
    assert '@router.get("/underlyings/{relationship}/{code}/series")' in markets_router
    assert 'percentile_cont' not in service
    assert 'moving_average' not in service
    assert 'pcr' not in service.lower()


def test_tushare_json_conversion_replaces_nonfinite_source_values_with_null():
    assert _json_safe(float("nan")) is None
    assert _json_safe(float("inf")) is None
    assert _json_safe(Decimal("NaN")) is None


def test_agentos_market_analysis_uses_formal_versioned_methodologies():
    service = (ROOT / "apps/api/services/agent_platform/tushare.py").read_text()
    router = (ROOT / "apps/api/routers/markets.py").read_text()
    for route in ('/valuation-board', '/correlations', '/factors'):
        assert f'@router.get("{route}")' in router
    for methodology in ("kt_valuation_percentile_v1", "kt_corr_v1", "kt_factor_v1", "kt_crowding_v1"):
        assert methodology in service
    assert "INTERVAL '5 years'" in service
    assert "crowding_percentile" in service
    assert 'reason_code="historical_coverage_partial"' in service
    assert "elapsed_days / (365.25 * 5)" in service
    assert '"publication_version": publication_version()' in service
    assert '"capability_version": capability_version()' in service
    assert '"synthetic_substitution": False' in service


def test_factor_returns_are_point_in_time_and_crowding_never_redistributes_missing_weights():
    service = (ROOT / "apps/api/services/agent_platform/tushare.py").read_text()
    assert "ann_date::text<=to_char(CAST(:start_date AS date),'YYYYMMDD')" in service
    assert '"historical_daily_basic_coverage_partial"' in service
    assert "end_px.trade_date=:as_of" in service
    assert '"point_in_time": True' in service
    assert '"turnover": 0.30' in service
    assert '"momentum_20d": 0.25' in service
    assert '"valuation_expansion_3m": 0.20' in service
    assert '"official_flow_5d_free_float": 0.25' in service
    assert '"unavailable_without_weight_redistribution"' in service
