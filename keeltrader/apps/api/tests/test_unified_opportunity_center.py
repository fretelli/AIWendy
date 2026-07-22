from pathlib import Path

import pytest

from services.agent_platform.opportunities import SourceUnavailable, _candidate, _domain_candidates, _options_candidates, _stable_hash


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
        return table in {"option_analytics_daily", "opt_basic"}

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
