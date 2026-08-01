from pathlib import Path

from services.agentos import AgentOSService


ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = ROOT / "migrations" / "versions"


def test_agentos_uses_additive_migrations_and_does_not_restore_today_or_thesis() -> None:
    names = {path.name for path in MIGRATIONS.glob("04*_agentos_*.py")}
    assert names == {
        "041_agentos_portfolio_foundation.py",
        "042_agentos_research_decisions.py",
        "043_agentos_document_versions.py",
        "044_agentos_instrument_identity.py",
        "045_agentos_report_fact_audit.py",
    }
    combined = "\n".join((MIGRATIONS / name).read_text(encoding="utf-8") for name in sorted(names))
    assert "today_items" not in combined
    assert "research_theses" not in combined
    assert 'down_revision = "040"' in (MIGRATIONS / "041_agentos_portfolio_foundation.py").read_text(encoding="utf-8")


def test_agentos_router_exposes_portfolio_research_strategy_and_download_contracts() -> None:
    source = (ROOT / "apps" / "api" / "routers" / "agentos.py").read_text(encoding="utf-8")
    for route in [
        "/os/overview",
        "/portfolio/accounts",
        "/portfolio/imports/preview",
        "/hypotheses",
        "/decisions",
        "/strategy-experiments",
        "/consensus",
        "/research-documents",
        "/research-document-versions/{version_id}/download",
    ]:
        assert route in source
    assert "broker" not in source.lower()
    assert "place_order" not in source


def test_bilingual_pdf_is_real_and_escapes_reportlab_markup() -> None:
    chinese = AgentOSService._render_pdf("中文 <标题>", "第一段 & 数据\n第二行", "zh-CN", {}, {"report": "A&B"})
    english = AgentOSService._render_pdf("English <Title>", "Evidence & conclusion", "en-US", {}, {"report": "A&B"})
    assert chinese.startswith(b"%PDF-")
    assert english.startswith(b"%PDF-")
    assert len(chinese) > 1_000
    assert len(english) > 1_000


def test_backtest_deducts_configured_transaction_costs() -> None:
    source = (ROOT / "apps" / "api" / "services" / "agentos.py").read_text(encoding="utf-8")
    assert 'parameters.get("cost_bps"' in source
    assert "turnover * cost_bps / 10_000" in source
    assert "point_in_time_factors" in source
    assert "fundamentals_parameter_ignored" in source
    assert '"cost_bps": cost_bps' in source


def test_agentos_models_keep_tenant_ownership_and_immutable_revision_tables() -> None:
    source = (ROOT / "apps" / "api" / "domain" / "agentos" / "models.py").read_text(encoding="utf-8")
    for table in [
        "portfolio_accounts",
        "portfolio_transactions",
        "research_hypotheses",
        "decision_records",
        "strategy_experiments",
        "research_documents",
    ]:
        assert f'__tablename__ = "{table}"' in source
    assert source.count("user_id = Column") >= 6
    assert '__tablename__ = "research_hypothesis_revisions"' in source
    assert '__tablename__ = "decision_revisions"' in source
    assert '__tablename__ = "strategy_run_versions"' in source
    assert '__tablename__ = "research_document_versions"' in source
    assert '__tablename__ = "research_document_downloads"' in source
    assert "fact_snapshot_sha256" in source
