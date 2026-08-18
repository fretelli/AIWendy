from pathlib import Path
from types import SimpleNamespace

import pytest

from services.agent_platform.opportunities import (
    PUBLICATION_WATERMARK_KEY,
    SourceUnavailable,
    _candidate,
    _domain_publication_watermark,
    _domain_candidates,
    _options_candidates,
    _publication_is_unchanged,
    _refresh_resource_lock,
    _stable_hash,
)


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def sample_candidate(source_date: str):
    return _candidate(
        domain="macro", playbook="macro_release_cpi", subject_type="indicator", subject_key="cpi",
        title="CPI", trigger="new release", hypothesis="test", affected_assets=["A股"],
        catalysts=["next release"], falsifiers=["revision"], source_dates={"cpi": source_date},
        evidence=[], freshness={"cpi": {"available": True, "as_of": source_date}},
    )


def test_opportunity_identity_is_stable_across_source_dates_but_snapshot_is_not():
    older = sample_candidate("2026-05")
    newer = sample_candidate("2026-06")
    assert older["fingerprint"] == newer["fingerprint"]
    assert _stable_hash(older, 64) != _stable_hash(newer, 64)


class FakeOptionReader:
    schema = "tushare"

    async def table_exists(self, table):
        return table in {"option_analytics_daily", "opt_basic", "opt_series_daily"}

    async def _execute_mappings(self, statement, params):
        self.sql = str(statement)
        return [
            {"opt_code": "IO", "trade_date": "2026-07-21", "nearest_maturity": "2026-08-21",
             "atm_iv": 0.2, "call_wing_iv": 0.22, "put_wing_iv": 0.24, "contracts": 12},
            {"opt_code": "IO", "trade_date": "2026-07-20", "nearest_maturity": "2026-08-21",
             "atm_iv": 0.2, "call_wing_iv": 0.22, "put_wing_iv": 0.24, "contracts": 10},
        ]


@pytest.mark.asyncio
async def test_convergence_count_alone_does_not_generate_option_opportunity():
    reader = FakeOptionReader()
    assert await _options_candidates(reader) == []
    assert "convergence_status='converged'" in reader.sql
    assert "opt_series_daily" in reader.sql
    assert "o.trade_date>=c.min_date" in reader.sql
    assert "a.opt_code=d.opt_code AND a.trade_date=d.trade_date" in reader.sql


def test_holder_watermark_uses_indexed_source_dates():
    source = (ROOT / "services/agent_platform/tushare.py").read_text()
    block = source.split("async def holder_source_watermark", 1)[1].split("async def search_holders", 1)[0]
    assert "MAX(ann_date)" in block
    assert "MAX(end_date)" in block
    assert "MAX(updated_at)" not in block


class MissingSourceReader:
    async def table_exists(self, table):
        return False


@pytest.mark.asyncio
async def test_missing_required_source_is_unavailable_not_zero():
    with pytest.raises(SourceUnavailable):
        await _domain_candidates("rates", MissingSourceReader())


def test_repo_comparison_is_partitioned_by_the_same_maturity():
    source = (ROOT / "services/agent_platform/opportunities.py").read_text()
    assert "PARTITION BY repo_maturity" in source
    assert "rn<=2" in source


def test_feed_is_read_only_and_user_actions_are_owned():
    router = (ROOT / "routers/markets.py").read_text()
    service = (ROOT / "services/agent_platform/opportunities.py").read_text()
    feed_block = router.split('@router.get("/opportunities")', 1)[1].split('@router.get("/opportunities/{opportunity_id}")', 1)[0]
    assert "refresh" not in feed_block
    assert '@router.post("/opportunities/{opportunity_id}/follow")' in router
    assert '@router.delete("/opportunities/{opportunity_id}/follow")' in router
    assert "AgentOpportunityFollow.user_id == self.user_id" in service
    assert "MarketOpportunity.user_id == self.user_id" in service
    assert "AgentCompanyEvidence.source_type == \"report\"" in service
    assert "研报仅有标题或缺少正文定位，不计为充分公司证据" in service


def test_snapshots_are_immutable_and_refresh_worker_is_isolated():
    service = (ROOT / "services/agent_platform/opportunities.py").read_text()
    worker = (ROOT / "tasks/opportunity_worker.py").read_text()
    assert "MarketOpportunitySnapshot(" in service
    assert "delete(MarketOpportunitySnapshot)" not in service
    assert "pg_try_advisory_lock" in service
    assert "opportunity-advisory-lock-keepalive" in service
    assert "OPPORTUNITY_LOCK_KEEPALIVE_SECONDS" in service
    assert "keeltrader:opportunity:heartbeat" in worker
    assert "existing_snapshot" in service
    assert "MarketOpportunitySnapshot.snapshot_fingerprint == snapshot_fingerprint" in service
    assert "desc(MarketOpportunitySnapshot.id)" in service


def test_unchanged_successful_publication_skips_heavy_refresh():
    state = SimpleNamespace(
        status="ok",
        source_watermark={PUBLICATION_WATERMARK_KEY: "datasets:abc"},
    )
    assert _publication_is_unchanged(state, "datasets:abc")
    assert not _publication_is_unchanged(state, "datasets:def")


def test_domain_publication_watermark_ignores_unrelated_datasets(monkeypatch):
    payload = {
        "available": True,
        "version": "global-1",
        "datasets": [
            {"key": "futures_daily", "actual_as_of": "2026-08-17", "last_success_at": "a", "points": 10, "state": "current"},
            {"key": "futures_mapping", "actual_as_of": "2026-08-17", "last_success_at": "a", "points": 5, "state": "current"},
            {"key": "stock_daily", "actual_as_of": "2026-08-17", "last_success_at": "a", "points": 20, "state": "current"},
        ],
    }
    monkeypatch.setattr(
        "services.agent_platform.opportunities.read_publication_status",
        lambda: payload,
    )
    first = _domain_publication_watermark("futures")
    payload["datasets"][2]["last_success_at"] = "b"
    assert _domain_publication_watermark("futures") == first
    payload["datasets"][0]["last_success_at"] = "b"
    assert _domain_publication_watermark("futures") != first


def test_optional_resource_lock_is_nonblocking(monkeypatch, tmp_path):
    lock_path = tmp_path / "shared-resource.lock"
    lock_path.touch()
    lock_path.chmod(0o444)
    monkeypatch.setenv("OPPORTUNITY_RESOURCE_LOCK_FILE", str(lock_path))
    with _refresh_resource_lock() as first:
        assert first
        with _refresh_resource_lock() as second:
            assert not second


def test_opportunity_detector_has_no_rank_percentile_or_execution_path():
    source = (ROOT / "services/agent_platform/opportunities.py").read_text().lower()
    assert "percentile" not in source
    assert "place_order" not in source
    assert "kelly" not in source
    assert '"score"' not in source


def test_migration_034_is_the_single_declared_head_and_documents_new_objects():
    migration = (REPO / "migrations/versions/034_unified_opportunity_center.py").read_text()
    assert 'revision = "034"' in migration
    assert 'down_revision = "033"' in migration
    assert "COMMENT ON TABLE market_opportunity_snapshots" in migration
    assert "COMMENT ON TABLE market_opportunity_refresh_state" in migration
