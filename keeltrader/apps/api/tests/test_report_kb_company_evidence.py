from unittest.mock import patch

import pytest

from services.agent_platform.report_kb import (
    ReportKBService,
    _company_identifiers,
    _query_terms,
    _report_matches_company,
)


def test_generic_research_words_are_not_company_identifiers():
    assert _query_terms("同益中 688722.SH 基本面 盈利 风险", ["同益中", "688722.SH"]) == [
        "同益中",
        "688722.SH",
        "688722",
    ]


def test_unrelated_industry_report_with_generic_word_is_rejected():
    report = {
        "title": "镍不锈钢日报：多重基本面因素共振",
        "excerpt": "沪镍价格大幅上行。",
        "metadata": {},
    }
    assert _report_matches_company(report, ["688722.SH", "同益中"]) is False


def test_numeric_code_substring_is_not_a_company_match():
    report = {"title": "代码 16887220 的行业统计", "excerpt": "无公司正文", "metadata": {}}
    assert _report_matches_company(report, ["688722.SH"]) is False


def test_company_name_or_trusted_structured_filter_is_accepted():
    body_match = {"title": "新材料行业", "excerpt": "同益中盈利能力改善", "metadata": {}}
    structured_match = {
        "title": "新材料行业",
        "excerpt": "盈利能力改善",
        "metadata": {
            "_search_company_filter_verified": True,
            "_search_company_identifiers": ["688722", "同益中"],
        },
    }
    assert _report_matches_company(body_match, ["同益中"]) is True
    assert _report_matches_company(structured_match, ["688722.SH"]) is True
    assert _company_identifiers(["688722.SH"]) == ["688722.sh", "688722"]


@pytest.mark.asyncio
async def test_empty_company_search_never_falls_back_to_recent_titles():
    with patch("services.agent_platform.report_kb._http_json", return_value={"results": []}) as http:
        rows = await ReportKBService().search_reports(
            "同益中 688722.SH 基本面",
            companies=["688722.SH", "同益中"],
            granularity="section",
        )

    assert rows == []
    assert http.call_count == 1


@pytest.mark.asyncio
async def test_semantic_result_is_filtered_again_on_the_client():
    response = {
        "results": [{
            "report_id": "r1",
            "section_id": "s1",
            "report_title": "镍不锈钢日报：多重基本面因素共振",
            "content": "沪镍价格大幅上行。",
            "section_type": "text",
            "granularity": "section",
            "page_number": 1,
            "metadata": {},
        }],
    }
    with patch("services.agent_platform.report_kb._http_json", return_value=response):
        rows = await ReportKBService().search_reports(
            "同益中 688722.SH 基本面",
            companies=["688722.SH", "同益中"],
            granularity="section",
        )

    assert rows == []
