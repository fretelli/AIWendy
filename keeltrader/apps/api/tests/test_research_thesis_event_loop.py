from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def test_today_and_thesis_backend_surfaces_are_retired():
    models = (ROOT / "domain/agent_platform/models.py").read_text(encoding="utf-8")
    router = (ROOT / "routers/agent_platform.py").read_text(encoding="utf-8")
    tools = (ROOT / "services/agent_platform/tools.py").read_text(encoding="utf-8")
    assert "class ResearchThesis" not in models
    assert "class ResearchEvent" not in models
    assert '@router.get("/theses")' not in router
    assert '@router.get("/events")' not in router
    assert '@router.get("/calendar")' not in router
    assert "get_research_thesis" not in tools
    assert "get_research_events" not in tools


def test_retirement_migration_deletes_feature_tables_and_allocation_links():
    migration = (REPO / "migrations/versions/037_retire_today_theses.py").read_text(encoding="utf-8")
    for table in ("allocation_policy_thesis_links", "research_thesis_evidence_links",
                  "research_thesis_versions", "research_theses", "research_events"):
        assert f"DROP TABLE IF EXISTS {table}" in migration
    assert 'down_revision = "036"' in migration


def test_data_status_is_read_only_and_china_curve_is_not_synthetic():
    markets = (ROOT / "routers/markets.py").read_text(encoding="utf-8")
    tushare = (ROOT / "services/agent_platform/tushare.py").read_text(encoding="utf-8")
    block = markets.split('@router.get("/data-status")', 1)[1].split('@router.get("/macro/series")', 1)[0]
    assert '"request_time_refresh": False' in block
    assert "refresh_opportunities_once" not in block
    assert "china_cash_treasury_curve" in tushare
    assert "不使用国债期货或其他价格伪造" in tushare
