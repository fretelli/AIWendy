from datetime import date

import pytest

from services.agent_platform.tushare import (
    _MACRO_FIELD_CATALOG,
    TushareReadService,
    build_macro_analysis,
    macro_freshness,
)


PPI_SOURCE_FIELDS = {
    f"ppi{dimension}_{measure}"
    for dimension in (
        "",
        "_mp",
        "_mp_qm",
        "_mp_rm",
        "_mp_p",
        "_cg",
        "_cg_f",
        "_cg_c",
        "_cg_adu",
        "_cg_dcg",
    )
    for measure in ("yoy", "mom", "accu")
}


def test_cpi_headline_is_official_yoy_and_percentile_uses_that_series():
    rows = []
    for year in range(2000, 2012):
        for month in range(1, 13):
            rows.append({
                "period": f"{year}{month:02d}",
                "nt_val": 90 + (year - 2000) * 1.2 + month / 10,
                "nt_mom": month / 100,
                "nt_yoy": (year - 2000) * 12 + month,
            })
    result = build_macro_analysis("cpi", rows)
    assert result["primary_field"] == "nt_yoy"
    assert result["summary"]["mom"]["method"] == "official"
    assert result["summary"]["mom"]["value"] == pytest.approx(.12)
    assert result["summary"]["yoy"]["status"] == "not_applicable"
    assert result["summary"]["percentile_10y"]["value"] == 100
    assert result["summary"]["percentile_10y"]["window_complete"] is True


def test_social_financing_avoids_misleading_mom_and_pmi_uses_unit_safe_calculations():
    social = build_macro_analysis("social_financing", [
        {"period": "202501", "inc_month": 100},
        {"period": "202502", "inc_month": 110},
        {"period": "202601", "inc_month": 120},
        {"period": "202602", "inc_month": 132},
    ])
    assert social["summary"]["mom"]["value"] is None
    assert social["summary"]["mom"]["status"] == "not_applicable"
    assert social["summary"]["mom"]["reason_code"] == "seasonal_monthly_flow"
    assert social["summary"]["yoy"]["value"] == pytest.approx(20)

    pmi = build_macro_analysis("pmi", [
        {"period": "202501", "pmi010000": 49.5},
        {"period": "202502", "pmi010000": 50.0},
        {"period": "202601", "pmi010000": 50.5},
        {"period": "202602", "pmi010000": 51.2},
    ])
    assert pmi["summary"]["mom"]["value"] == pytest.approx(.7)
    assert pmi["summary"]["yoy"]["value"] == pytest.approx(1.2)
    assert pmi["summary"]["mom"]["unit"] == "点"


def test_rates_compare_nearest_prior_observation_in_basis_points():
    result = build_macro_analysis("shibor", [
        {"period": date(2025, 1, 30), "3m": 1.80},
        {"period": date(2025, 12, 30), "3m": 1.90},
        {"period": date(2026, 1, 30), "3m": 2.05},
    ])
    assert result["summary"]["mom"]["value"] == pytest.approx(15)
    assert result["summary"]["yoy"]["value"] == pytest.approx(25)
    assert result["summary"]["mom"]["unit"] == "bp"


def test_gdp_headline_and_sequential_change_are_official_yoy_percentage_points():
    gdp = build_macro_analysis("gdp", [
        {"period": "2026Q1", "gdp": 100, "gdp_yoy": 5.0},
        {"period": "2026Q2", "gdp": 220, "gdp_yoy": 5.2},
    ])
    assert gdp["primary_field"] == "gdp_yoy"
    assert gdp["summary"]["primary"]["value"] == pytest.approx(5.2)
    assert gdp["summary"]["mom"]["value"] == pytest.approx(.2)
    assert gdp["summary"]["mom"]["unit"] == "个百分点"
    assert gdp["summary"]["yoy"]["status"] == "not_applicable"

    ppi = build_macro_analysis("ppi", [{"period": "202606", "ppi_yoy": -1.2, "ppi_mom": .1}])
    assert ppi["primary_alias"] == "yoy"
    assert ppi["summary"]["primary"]["value"] == pytest.approx(-1.2)
    assert ppi["summary"]["yoy"]["status"] == "not_applicable"


def test_ppi_drilldown_exposes_every_authorized_numeric_provider_field():
    fields = {item["key"] for item in _MACRO_FIELD_CATALOG["ppi"]}
    assert fields == PPI_SOURCE_FIELDS
    assert len(fields) == 30
    assert next(item for item in _MACRO_FIELD_CATALOG["ppi"] if item["key"] == "ppi_mp_qm_yoy") == {
        "key": "ppi_mp_qm_yoy",
        "label": "采掘工业同比",
        "unit": "%",
        "group": "生产资料",
    }


def test_money_supply_headline_is_m2_yoy_and_credit_percentile_is_same_calendar_month():
    money = build_macro_analysis("money_supply", [
        {"period": "202501", "m2": 3000000, "m2_yoy": 7.0},
        {"period": "202502", "m2": 3100000, "m2_yoy": 7.4},
    ])
    assert money["primary_field"] == "m2_yoy"
    assert money["summary"]["primary"]["value"] == pytest.approx(7.4)

    social_rows = []
    for year in range(2017, 2027):
        social_rows.extend([
            {"period": f"{year}01", "inc_month": 100 + year - 2017},
            {"period": f"{year}02", "inc_month": 1000 + year - 2017},
        ])
    social = build_macro_analysis("social_financing", social_rows)
    latest = social["series"]["percentile_10y"]["rows"][-1]
    assert latest["sample_count"] == 10
    assert latest["value"] == 100
    assert social["series"]["percentile_10y"]["meta"]["formula"] == "percent_rank_inc_same_calendar_month_trailing_10_years"


@pytest.mark.asyncio
async def test_macro_catalog_preserves_rates_and_keeps_fiscal_gap_explicit():
    reader = TushareReadService(None)
    requested = []

    async def detail(key):
        requested.append(key)
        return {"key": key, "table": "cn_gdp", "available": True, "domain": "macro"}

    async def fields(_tables):
        return {"cn_gdp": ["gdp_yoy"]}

    reader._macro_detail = detail
    reader._numeric_fields = fields
    catalog = await reader.macro_catalog()
    assert "shibor" in requested
    assert "lpr" in requested
    assert "us_treasury" in requested
    assert "us_real_treasury" in requested
    fiscal = next(item for item in catalog["items"] if item["key"] == "fiscal")
    assert fiscal["available"] is False
    assert fiscal["reason_code"] == "provider_dataset_unavailable"
    assert catalog["methodology"]["synthetic_substitution"] is False


def test_rates_catalog_registers_authorized_private_lending_history():
    definitions = TushareReadService.rates_definitions()
    assert definitions["wenzhou_private"] == (
        "wz_index", "date", "historical", "温州民间融资综合利率（历史）",
    )
    assert definitions["guangzhou_private"] == (
        "gz_index", "date", "historical", "广州民间借贷利率（历史）",
    )


def test_macro_freshness_marks_old_monthly_and_quarterly_data_stale():
    assert macro_freshness("202607", "monthly", date(2026, 8, 17))["freshness_state"] == "current"
    stale_month = macro_freshness("202510", "monthly", date(2026, 8, 17))
    assert stale_month["freshness_state"] == "stale"
    assert stale_month["lag_days"] > stale_month["max_lag_days"]
    assert macro_freshness("2026Q1", "quarterly", date(2026, 8, 17))["freshness_state"] == "stale"


@pytest.mark.asyncio
async def test_eco_cal_series_is_hidden_until_coverage_gate_is_met(monkeypatch):
    monkeypatch.setattr("services.agent_platform.tushare.physical_tables", lambda: frozenset({"macro_release_series"}))
    reader = TushareReadService(None)

    async def execute(_query, _params):
        return [{"period": f"2025{month:02d}", "actual_value": month} for month in range(1, 12)]

    reader._execute_mappings = execute
    detail = await reader._macro_detail("industrial_production_yoy")
    assert detail["available"] is False
    assert detail["reason_code"] == "insufficient_release_coverage"
    assert detail["quality"]["coverage_points"] == 11
    assert detail["quality"]["minimum_samples"] == 12


@pytest.mark.asyncio
async def test_macro_field_query_requires_the_explicit_professional_catalog():
    reader = TushareReadService(None)

    async def fields(_tables):
        return {"cn_gdp": ["gdp_yoy", "created_at"]}

    reader._numeric_fields = fields
    with pytest.raises(ValueError, match="Unknown macro source field"):
        await reader.macro_series("gdp", "created_at")
