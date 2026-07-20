from pathlib import Path

from services.agent_platform.holders import normalize_holder_name
from services.agent_platform.tushare import _build_holder_cost_estimates


ROOT = Path(__file__).resolve().parents[3]


def test_holder_name_normalization_is_conservative():
    assert normalize_holder_name("  徐　开东  ") == "徐 开东"
    assert normalize_holder_name("香港中央结算有限公司") == "香港中央结算有限公司"


def test_holder_migration_is_user_scoped_and_private():
    source = (ROOT / "migrations/versions/029_holder_radar.py").read_text(encoding="utf-8")
    assert "agent_holder_watchlist" in source
    assert "user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE" in source
    assert "agent_holder_events" in source
    assert "uq_agent_holder_event_period" in source


def test_holder_queries_use_each_company_latest_period_and_explicit_exit_language():
    source = (ROOT / "apps/api/services/agent_platform/tushare.py").read_text(encoding="utf-8")
    assert "MAX(source.end_date) AS end_date" in source
    assert "exited_top10" in source
    assert "holder_name = ANY(:holder_names)" in source


def test_holder_history_classifies_full_timeline_before_recent_window_and_estimates_prices():
    source = (ROOT / "apps/api/services/agent_platform/tushare.py").read_text(encoding="utf-8")
    history = source.split("async def holder_history(", 1)[1].split("async def query_table(", 1)[0]
    assert "result_filter = \"AND classified.end_date >= :min_end_date\"" in source
    assert "price.adj_type = 'qfq'" in source
    assert "price.trade_date > TO_DATE(paged.previous_end_date, 'YYYYMMDD')" in source
    assert "qfq_close_volume_weighted_reporting_window" in source
    assert "退出前十仅表示后续榜单未出现" in source
    company_periods = history.split("), company_periods AS (", 1)[1].split("), positions AS (", 1)[0]
    positions = history.split("), positions AS (", 1)[1].split("), positioned AS (", 1)[0]
    assert "min_end_date" not in company_periods
    assert "min_end_date" not in positions
    scanner = (ROOT / "apps/api/services/agent_platform/holders.py").read_text(encoding="utf-8")
    assert "include_price_estimates=False" in scanner


def test_holder_tools_do_not_add_scoring_or_sourcing():
    source = (ROOT / "apps/api/services/agent_platform/tools.py").read_text(encoding="utf-8")
    assert '"search_holder"' in source
    assert '"holder_positions"' in source
    assert '"holder_history"' in source
    assert '"source_by_holders"' not in source


def test_current_holder_cost_ledger_preserves_unknown_basis_and_reduces_proportionally():
    estimates = _build_holder_cost_estimates([
        {"ts_code": "000001.SZ", "end_date": "20200331", "event_type": "first_seen", "hold_amount": 100},
        {"ts_code": "000001.SZ", "end_date": "20200630", "event_type": "increased", "hold_amount": 150,
         "previous_hold_amount": 100, "hold_change": 50, "estimate_low": 8, "estimate_high": 12,
         "estimate_volume_weighted_price": 10},
        {"ts_code": "000001.SZ", "end_date": "20200930", "event_type": "reduced", "hold_amount": 75,
         "previous_hold_amount": 150, "hold_change": -75},
    ])
    estimate = estimates["000001.SZ"]
    assert estimate["unit_cost"] == 10
    assert estimate["unit_cost_low"] == 8
    assert estimate["unit_cost_high"] == 12
    assert estimate["covered_shares"] == 25
    assert estimate["coverage_ratio"] == 1 / 3
    assert estimate["estimated_position_cost"] is None


def test_current_holder_cost_ledger_resets_after_observed_exit_and_reentry():
    estimates = _build_holder_cost_estimates([
        {"ts_code": "000001.SZ", "end_date": "20200331", "event_type": "first_seen", "hold_amount": 100},
        {"ts_code": "000001.SZ", "end_date": "20200630", "event_type": "exited_top10", "hold_amount": None,
         "previous_hold_amount": 100},
        {"ts_code": "000001.SZ", "end_date": "20200930", "event_type": "new", "hold_amount": 80,
         "estimate_low": 4, "estimate_high": 6, "estimate_volume_weighted_price": 5},
    ])
    estimate = estimates["000001.SZ"]
    assert estimate["unit_cost"] == 5
    assert estimate["covered_shares"] == 80
    assert estimate["coverage_ratio"] == 1
    assert estimate["estimated_position_cost"] == 400


def test_current_holder_cost_ledger_preserves_qfq_unit_cost_across_share_adjustments():
    estimates = _build_holder_cost_estimates([
        {"ts_code": "000001.SZ", "end_date": "20200331", "event_type": "new", "hold_amount": 100,
         "estimate_low": 4, "estimate_high": 6, "estimate_volume_weighted_price": 5},
        {"ts_code": "000001.SZ", "end_date": "20200630", "event_type": "increased", "hold_amount": 200,
         "previous_hold_amount": 100, "hold_change": 0},
    ])
    estimate = estimates["000001.SZ"]
    assert estimate["unit_cost"] == 5
    assert estimate["covered_shares"] == 200
    assert estimate["estimated_position_cost"] == 1000
