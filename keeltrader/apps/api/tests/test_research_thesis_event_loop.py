from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def test_thesis_and_event_models_are_user_scoped_and_unscored():
    models = (ROOT / "domain/agent_platform/models.py").read_text(encoding="utf-8")
    service = (ROOT / "services/agent_platform/research_loop.py").read_text(encoding="utf-8")
    assert "class ResearchThesis" in models and "class ResearchEvent" in models
    assert "ResearchThesis.user_id == self.user_id" in service
    assert "ResearchEvent.user_id == self.user_id" in service
    assert '"scoring": False' in service
    assert "percentile" not in service.lower()
    assert "ranking" not in service.lower()


def test_report_title_only_is_rejected_as_thesis_evidence():
    service = (ROOT / "services/agent_platform/research_loop.py").read_text(encoding="utf-8")
    assert 'citation.get("excerpt")' in service
    assert 'citation.get("section_id") or citation.get("page_number") is not None' in service
    assert "Report evidence requires a body excerpt and page or section location" in service


def test_event_producers_are_idempotent_and_do_not_flood_baselines():
    opportunities = (ROOT / "services/agent_platform/opportunities.py").read_text(encoding="utf-8")
    dossier = (ROOT / "services/agent_platform/dossier.py").read_text(encoding="utf-8")
    holders = (ROOT / "services/agent_platform/holders.py").read_text(encoding="utf-8")
    loop = (ROOT / "services/agent_platform/research_loop.py").read_text(encoding="utf-8")
    assert "on_conflict_do_nothing" in loop
    assert "if latest is not None" in opportunities
    assert 'AgentOpportunityFollow.state != "paused"' in opportunities
    assert "if previous is not None" in dossier
    assert 'if not initial and row["event_type"] != "unchanged"' in holders


def test_migration_is_additive_and_every_new_object_has_comments():
    migration = (REPO / "migrations/versions/035_research_thesis_event_loop.py").read_text(encoding="utf-8")
    for table in ("research_theses", "research_thesis_versions", "research_thesis_evidence_links", "research_events"):
        assert f"COMMENT ON TABLE {table}" in migration
    assert 'down_revision = "034"' in migration
    assert "intentionally non-reversible" in migration


def test_data_status_is_read_only_and_china_curve_is_not_synthetic():
    markets = (ROOT / "routers/markets.py").read_text(encoding="utf-8")
    tushare = (ROOT / "services/agent_platform/tushare.py").read_text(encoding="utf-8")
    block = markets.split('@router.get("/data-status")', 1)[1].split('@router.get("/macro/series")', 1)[0]
    assert '"request_time_refresh": False' in block
    assert "refresh_opportunities_once" not in block
    assert "china_cash_treasury_curve" in tushare
    assert "不使用国债期货或其他价格伪造" in tushare
