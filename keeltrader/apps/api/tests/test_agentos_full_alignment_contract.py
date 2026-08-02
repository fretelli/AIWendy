from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "apps" / "api"


def test_agentos_exposes_real_portfolio_research_and_safe_trace_contracts():
    router = (API / "routers" / "agentos.py").read_text()
    platform = (API / "routers" / "agent_platform.py").read_text()
    assert '"/portfolio/accounts/{account_id}/analytics"' in router
    assert '"/portfolio/accounts/{account_id}/holdings/{instrument_id}/detail"' in router
    assert '"/research/library"' in router
    assert '"/research/library/status"' in router
    assert '"/research/library/{report_id}/pdf"' in router
    assert '"/research-documents/{document_id}/generate-bilingual"' in router
    assert '"/runs/{run_id}/trace"' in platform
    assert '"/schedules/{schedule_id}"' in platform
    assert 'safe_summary_only' in platform


def test_allocation_publish_is_transactional_and_strategy_inputs_are_backend_owned():
    allocation_router = (API / "routers" / "allocation.py").read_text()
    wealth = (API / "services" / "agent_platform" / "wealth.py").read_text()
    agentos_router = (API / "routers" / "agentos.py").read_text()
    assert '"/allocation-policy-versions/{version_id}/publish-saa"' in allocation_router
    assert "publish_allocation_policy_as_saa" in wealth
    assert "with_for_update" in wealth
    assert "deprecated=True" in agentos_router
    assert "backend joins point-in-time published fundamentals" in agentos_router


def test_bilingual_generation_uses_one_fact_snapshot_and_two_real_pdf_locales():
    service = (API / "services" / "agentos.py").read_text()
    assert "generate_bilingual_document" in service
    assert '"zh-CN"' in service and '"en-US"' in service
    assert "fact_snapshot_sha256" in service
    assert 'pdf.startswith(b"%PDF")' in service
