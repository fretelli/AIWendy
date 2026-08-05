from unittest.mock import AsyncMock

import pytest

from services.agent_platform import market_cache
from services.agent_platform import tushare as tushare_module
from services.agent_platform.tushare import TushareReadService


@pytest.mark.asyncio
async def test_snapshot_reader_preserves_payload_and_adds_materialization_metadata(monkeypatch):
    monkeypatch.setattr(tushare_module, "queryable_tables", lambda: frozenset({"market_valuation_snapshot"}))
    monkeypatch.setattr(tushare_module, "publication_version", lambda: "publication-v1")
    monkeypatch.setattr(tushare_module, "capability_version", lambda: "capability-v1")
    reader = TushareReadService(None)
    reader._execute_mappings = AsyncMock(return_value=[{
        "analysis_version": "analysis-v1",
        "computed_at": "2026-08-03T10:00:00Z",
        "source_watermarks": {"sw_daily": "2026-08-01"},
        "payload": {"metadata": {"status": "available", "methodology_key": "kt_valuation_percentile_v2",
                                  "source_datasets": ["sw_daily"]},
                    "items": [{"code": "801010.SI"}], "percentile_window": "5Y",
                    "synthetic_substitution": False},
    }])
    result = await reader.valuation_snapshot()
    assert result["items"] == [{"code": "801010.SI"}]
    assert result["metadata"]["materialization_version"] == "analysis-v1"
    assert result["metadata"]["publication_version"] == "publication-v1"
    assert result["metadata"]["source_watermarks"] == {"sw_daily": "2026-08-01"}
    query_parameters = reader._execute_mappings.await_args.args[1]
    assert query_parameters["methodology"] == "kt_valuation_percentile_v2"


@pytest.mark.asyncio
async def test_missing_materialized_capability_returns_immediately(monkeypatch):
    monkeypatch.setattr(tushare_module, "queryable_tables", lambda: frozenset())
    reader = TushareReadService(None)
    reader._execute_mappings = AsyncMock()
    result = await reader.factor_snapshot()
    assert result["metadata"]["status"] == "unavailable"
    assert result["metadata"]["reason_code"] == "materialized_capability_unavailable"
    reader._execute_mappings.assert_not_awaited()


@pytest.mark.asyncio
async def test_market_history_readers_filter_methodology(monkeypatch):
    monkeypatch.setattr(tushare_module, "queryable_tables", lambda: frozenset({
        "market_correlation_snapshot", "market_factor_snapshot",
    }))
    reader = TushareReadService(None)
    reader._execute_mappings = AsyncMock(return_value=[])
    await reader.correlation_history(60, 120)
    assert reader._execute_mappings.await_args.args[1]["methodology"] == "kt_corr_v1"
    await reader.factor_history(120)
    assert reader._execute_mappings.await_args.args[1]["methodology"] == "kt_factor_v1"


@pytest.mark.asyncio
async def test_market_history_readers_deduplicate_as_of_and_allow_five_year_limit(monkeypatch):
    monkeypatch.setattr(tushare_module, "queryable_tables", lambda: frozenset({
        "market_correlation_snapshot", "market_factor_snapshot",
    }))
    reader = TushareReadService(None)
    reader._execute_mappings = AsyncMock(return_value=[])
    await reader.correlation_history(60, 1260)
    correlation_query = str(reader._execute_mappings.await_args.args[0])
    assert "DISTINCT ON(as_of)" in correlation_query
    assert "ORDER BY as_of DESC,computed_at DESC" in correlation_query
    assert reader._execute_mappings.await_args.args[1]["limit"] == 1260
    await reader.factor_history(1260)
    factor_query = str(reader._execute_mappings.await_args.args[0])
    assert "DISTINCT ON(as_of)" in factor_query
    assert reader._execute_mappings.await_args.args[1]["limit"] == 1260


def test_market_cache_key_binds_both_publication_versions(monkeypatch):
    monkeypatch.setattr(market_cache, "publication_version", lambda: "p1")
    monkeypatch.setattr(market_cache, "capability_version", lambda: "c1")
    assert market_cache.market_cache_key("factors") == "markets:v5:p1:c1:factors"
