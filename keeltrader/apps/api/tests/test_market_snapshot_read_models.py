from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest

from services.agent_platform import market_cache
from services.agent_platform import tushare as tushare_module
from services.agent_platform.tushare import TushareReadService
from routers.markets import _a_share_provider_symbol


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
        "payload": {"metadata": {"status": "available", "methodology_key": "kt_valuation_percentile_v3",
                                  "source_datasets": ["sw_daily"]},
                    "items": [{"code": "801010.SI"}], "membership_map": {"000001.SZ": {"code": "801780.SI"}},
                    "percentile_window": "5Y",
                    "synthetic_substitution": False},
    }])
    result = await reader.valuation_snapshot()
    assert result["items"] == [{"code": "801010.SI"}]
    assert "membership_map" not in result
    assert result["metadata"]["materialization_version"] == "analysis-v1"
    assert result["metadata"]["publication_version"] == "publication-v1"
    assert result["metadata"]["source_watermarks"] == {"sw_daily": "2026-08-01"}
    query_parameters = reader._execute_mappings.await_args.args[1]
    assert query_parameters["methodology"] == "kt_valuation_percentile_v3"


@pytest.mark.asyncio
async def test_valuation_history_reads_only_versioned_snapshots(monkeypatch):
    monkeypatch.setattr(tushare_module, "queryable_tables", lambda: frozenset({"market_valuation_snapshot"}))
    reader = TushareReadService(None)
    reader._execute_mappings = AsyncMock(return_value=[{
        "analysis_version": "v1", "as_of": "2026-08-01",
        "available_points_total": 9, "methodology": {"cross_universe_comparable": False},
        "item": {"code": "801010.SI", "universe": "sw_l1", "trade_date": "2026-08-01",
                 "pe": 12.3, "pb": 1.5, "pe_percentile": .4,
                 "pe_basis": "provider_defined", "pe_source_field": "sw_daily.pe",
                 "pb_basis": "provider_defined", "pb_source_field": "sw_daily.pb",
                 "comparison_group": "sw_l1_provider_pe"},
    }])
    result = await reader.valuation_history("801010.SI", "sw_l1", 1260)
    assert result["points"][0]["pe"] == 12.3
    assert result["available_start"] == "2026-08-01"
    assert result["available_points_total"] == 9
    assert result["metadata"]["coverage"] == 9 / 1260
    assert result["methodology"]["cross_universe_comparable"] is False
    assert result["cross_universe_comparable"] is False
    assert result["points"][0]["pe_source_field"] == "sw_daily.pe"
    assert result["points"][0]["comparison_group"] == "sw_l1_provider_pe"
    query = str(reader._execute_mappings.await_args.args[0])
    assert "market_valuation_snapshot" in query
    assert "DISTINCT ON(as_of)" in query
    assert "COUNT(*) OVER()" in query
    assert reader._execute_mappings.await_args.args[1]["limit"] == 1260
    assert reader._execute_mappings.await_args.args[1]["methodology"] == "kt_valuation_percentile_v3"


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


def test_held_industry_symbol_normalization_only_accepts_a_share_stocks():
    assert _a_share_provider_symbol(SimpleNamespace(
        market="CN", instrument_type="stock", provider_symbol="600000", symbol="600000",
    )) == "600000.SH"
    assert _a_share_provider_symbol(SimpleNamespace(
        market="CN", instrument_type="stock", provider_symbol=None, symbol="000001",
    )) == "000001.SZ"
    assert _a_share_provider_symbol(SimpleNamespace(
        market="HK", instrument_type="stock", provider_symbol="00700.HK", symbol="00700",
    )) is None
    assert _a_share_provider_symbol(SimpleNamespace(
        market="CN", instrument_type="etf", provider_symbol="510300.SH", symbol="510300",
    )) is None
