from services.agent_platform.dossier import (
    CALCULATION_VERSION,
    _canonical_rows,
    _growth,
    _implemented_dividend_yield,
    _ratio,
    _report_evidence_state,
    _report_has_content,
    _ttm,
)


def test_canonical_rows_keep_latest_disclosure_per_period():
    rows = [
        {"end_date": "20250331", "ann_date": "20250420", "revenue": 1},
        {"end_date": "20250331", "ann_date": "20250428", "revenue": 2},
        {"end_date": "20241231", "ann_date": "20250320", "revenue": 3},
    ]
    canonical = _canonical_rows(rows)
    assert [row["end_date"] for row in canonical] == ["20250331", "20241231"]
    assert canonical[0]["revenue"] == 2


def test_luolai_golden_same_period_yoy_and_ttm_valuations():
    income = [
        {"end_date": "20250331", "ann_date": "20250428", "revenue": 1_050_000_000,
         "n_income_attr_p": 100_000_000},
        {"end_date": "20241231", "ann_date": "20250328", "revenue": 4_961_500_000,
         "n_income_attr_p": 500_000_000},
        {"end_date": "20240331", "ann_date": "20240428", "revenue": 991_501_416,
         "n_income_attr_p": 45_620_000},
    ]
    revenue_ttm, _ = _ttm(income, "revenue")
    profit_ttm, _ = _ttm(income, "n_income_attr_p")
    market_cap = 9_034_000_000

    assert round(_growth(1_050_000_000, 991_501_416), 1) == 5.9
    assert round(profit_ttm / 1_000_000, 2) == 554.38
    assert round(_ratio(market_cap, profit_ttm), 1) == 16.3
    assert round(_ratio(market_cap, 4_300_000_000), 1) == 2.1
    assert round(_ratio(market_cap, revenue_ttm), 1) == 1.8


def test_dividend_yield_uses_only_implemented_trailing_cash_dividends():
    rows = [
        {"end_date": "20241231", "div_proc": "实施", "pay_date": "20250701", "cash_div_tax": 0.37},
        {"end_date": "20250630", "div_proc": "预案", "pay_date": "20250705", "cash_div_tax": 0.20},
        {"end_date": "20231231", "div_proc": "实施", "pay_date": "20240601", "cash_div_tax": 0.30},
    ]
    value, periods = _implemented_dividend_yield(rows, 9.47, "20250710")
    assert round(value, 1) == 3.9
    assert periods == ["20241231"]


def test_calculation_contract_is_versioned():
    assert CALCULATION_VERSION == "fundamental-v3"


def test_report_evidence_requires_verified_company_and_body_location():
    title_only = {
        "title": "同益中公司深度报告",
        "excerpt": "同益中公司深度报告",
        "company_match_verified": True,
    }
    valid = {
        "title": "同益中公司深度报告",
        "excerpt": "同益中盈利能力持续改善。",
        "section_id": "section-1",
        "company_match_verified": True,
    }
    unverified = {**valid, "company_match_verified": False}

    assert _report_has_content(title_only) is False
    assert _report_has_content(unverified) is False
    assert _report_has_content(valid) is True


def test_report_evidence_state_distinguishes_absent_processing_and_unlocatable():
    assert _report_evidence_state([], []) == (
        "no_company_report",
        "知识库中尚未找到与该公司名称或证券代码精确匹配的研报。",
    )
    assert _report_evidence_state([], [{"sections_count": 0, "ingest_status": "partial"}])[0] == "company_report_processing"
    assert _report_evidence_state([], [{"sections_count": 4, "ingest_status": "completed"}])[0] == "company_report_not_locatable"
    assert _report_evidence_state([{"section_id": "1"}], [])[0] == "sufficient"
