"""AgentOS v1 smoke tests."""

from datetime import datetime
from uuid import uuid4

import pytest

from services.agentos.decisions import AgentOSDecisionService
from services.agentos.metrics import deflated_sharpe_ratio_proxy, summarize_trade_returns
from services.agentos.report_kb import ReportKBService
from services.agentos.serializers import serialize
from services.agentos.tushare_read import TushareReadService


def test_agentos_health(client):
    response = client.get("/api/v1/agentos/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["tushare_token_required"] is False


def test_backtest_metrics_penalize_trials():
    returns = [2, -1, 3, -0.5, 1.5, 2.2]
    one_trial = summarize_trade_returns(returns, trials=1)
    many_trials = summarize_trade_returns(returns, trials=100)
    assert one_trial["total_trades"] == 6
    assert many_trials["deflated_sharpe_proxy"] < one_trial["deflated_sharpe_proxy"]
    assert one_trial["dsr_method"] == "conservative_proxy_v1"
    assert one_trial["research_only"] is True


def test_dsr_proxy_handles_small_samples():
    assert deflated_sharpe_ratio_proxy(1.2, observations=1, trials=10) == 0.0


@pytest.mark.asyncio
async def test_tushare_query_rejects_unallowlisted_table():
    svc = TushareReadService(session=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        await svc.query_table("pg_catalog.pg_user")


def test_agentos_serializer_handles_datetime_uuid_and_nested_values():
    item_id = uuid4()
    now = datetime(2026, 1, 2, 3, 4, 5)
    assert serialize({"id": item_id, "items": [{"created_at": now}]}) == {
        "id": str(item_id),
        "items": [{"created_at": "2026-01-02T03:04:05"}],
    }


@pytest.mark.asyncio
async def test_decision_service_records_research_only_decision():
    session = _FakeSession()
    svc = AgentOSDecisionService(session)  # type: ignore[arg-type]
    user_id = uuid4()

    decision = await svc.record_decision(
        user_id,
        {
            "symbol": "000001.SZ",
            "action": "watch",
            "thesis": "Research support only.",
            "confidence": 0.1,
        },
    )

    assert decision.user_id == user_id
    assert decision.symbol == "000001.SZ"
    assert decision.human_decision == "pending"
    assert decision.decided_at is None
    assert decision.position_plan == {}
    assert session.added == [decision]
    assert session.flushed is True


@pytest.mark.asyncio
async def test_report_kb_search_falls_back_to_recent_candidates(monkeypatch):
    def fake_http_json(method, path, payload=None):
        if method == "POST" and path == "/search":
            return {"results": []}
        if method == "GET" and path.startswith("/reports/recent-candidates"):
            return [
                {
                    "id": "r1",
                    "title": "平安银行 资产质量跟踪",
                    "summary": "平安银行零售业务更新",
                    "broker": "Test Broker",
                    "report_date": "2026-01-02",
                },
                {
                    "id": "r2",
                    "title": " unrelated ",
                    "summary": "other",
                    "broker": "Test Broker",
                    "report_date": "2026-01-01",
                },
            ]
        return {}

    monkeypatch.setattr("services.agentos.report_kb._http_json", fake_http_json)

    hits = await ReportKBService().search_reports("平安银行 投资 研报", top_k=3)

    assert len(hits) == 1
    assert hits[0]["report_id"] == "r1"
    assert hits[0]["metadata"]["fallback"] is True


class _FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True
