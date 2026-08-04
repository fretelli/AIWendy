from datetime import date

import pytest

from services.agent_platform.tushare import build_macro_analysis


def test_official_cpi_changes_and_partial_ten_year_percentile_are_explicit():
    rows = []
    for year in range(2000, 2012):
        for month in range(1, 13):
            rows.append({
                "period": f"{year}{month:02d}",
                "nt_val": 90 + (year - 2000) * 1.2 + month / 10,
                "nt_mom": month / 100,
                "nt_yoy": year - 2000,
            })
    result = build_macro_analysis("cpi", rows)
    assert result["primary_field"] == "nt_val"
    assert result["summary"]["mom"]["method"] == "official"
    assert result["summary"]["mom"]["value"] == pytest.approx(.12)
    assert result["summary"]["yoy"]["source_field"] == "nt_yoy"
    assert result["summary"]["percentile_10y"]["value"] == 100
    assert result["summary"]["percentile_10y"]["window_complete"] is True


def test_social_financing_and_pmi_use_unit_safe_calculations():
    social = build_macro_analysis("social_financing", [
        {"period": "202501", "inc": 100},
        {"period": "202502", "inc": 110},
        {"period": "202601", "inc": 120},
        {"period": "202602", "inc": 132},
    ])
    assert social["summary"]["mom"]["value"] == pytest.approx(10)
    assert social["summary"]["yoy"]["value"] == pytest.approx(20)
    assert social["summary"]["mom"]["method"] == "calculated"

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


def test_gdp_qoq_is_not_applicable_and_ppi_primary_is_official_yoy():
    gdp = build_macro_analysis("gdp", [{"period": "2026Q2", "gdp": 100, "gdp_yoy": 5.2}])
    assert gdp["summary"]["mom"]["status"] == "not_applicable"
    assert gdp["summary"]["mom"]["reason_code"] == "official_qoq_unavailable"
    assert gdp["summary"]["yoy"]["value"] == pytest.approx(5.2)

    ppi = build_macro_analysis("ppi", [{"period": "202606", "ppi_yoy": -1.2, "ppi_mp": .1}])
    assert ppi["primary_alias"] == "yoy"
    assert ppi["summary"]["primary"]["value"] == pytest.approx(-1.2)
    assert ppi["summary"]["yoy"]["value"] == pytest.approx(-1.2)
