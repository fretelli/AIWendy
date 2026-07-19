from pathlib import Path

from services.agent_platform.holders import normalize_holder_name


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


def test_holder_tools_do_not_add_scoring_or_sourcing():
    source = (ROOT / "apps/api/services/agent_platform/tools.py").read_text(encoding="utf-8")
    assert '"search_holder"' in source
    assert '"holder_positions"' in source
    assert '"holder_history"' in source
    assert '"source_by_holders"' not in source
