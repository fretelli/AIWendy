from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.agent_platform.wealth import WealthService, age_on, horizon_bucket


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def test_single_person_household_age_and_lifecycle_boundaries_are_supported():
    assert age_on(date(1990, 7, 25), date(2026, 7, 24)) == 35
    assert age_on(date(1990, 7, 24), date(2026, 7, 24)) == 36
    source = (ROOT / "services/agent_platform/wealth.py").read_text()
    assert "bool(members) and not conflicts" in source
    assert "家庭财富档案只能有一名本人" in source


def test_horizon_buckets_include_24_and_60_month_boundaries():
    today = date(2026, 7, 24)
    assert horizon_bucket(date(2028, 7, 24), today=today) == "short"
    assert horizon_bucket(date(2031, 7, 24), today=today) == "medium"
    assert horizon_bucket(date(2031, 8, 24), today=today) == "long"


def test_saa_targets_require_complete_weight_and_valid_bands():
    valid = [
        {"key": "safety", "target_weight": 0.3, "min_weight": 0.3, "max_weight": 0.3},
        {"key": "market", "target_weight": 0.7, "min_weight": 0.5, "max_weight": 0.8},
    ]
    WealthService._validate_targets(valid)
    with pytest.raises(ValueError, match="100%"):
        WealthService._validate_targets([{**valid[0], "target_weight": 0.2, "min_weight": 0.1}, valid[1]])
    with pytest.raises(ValueError, match="下限"):
        WealthService._validate_targets([{**valid[0], "min_weight": 0.4}, valid[1]])
    with pytest.raises(ValueError, match="不能重复"):
        WealthService._validate_targets([valid[0], {**valid[1], "key": "safety"}])


def test_taa_is_zero_sum_band_limited_safety_locked_and_at_most_180_days():
    saa = SimpleNamespace(targets=[
        {"key": "safety", "label": "安全层", "layer": "safety", "target_weight": 0.3, "min_weight": 0.3, "max_weight": 0.3},
        {"key": "core", "label": "核心", "layer": "market", "target_weight": 0.5, "min_weight": 0.4, "max_weight": 0.6},
        {"key": "satellite", "label": "卫星", "layer": "market", "target_weight": 0.2, "min_weight": 0.1, "max_weight": 0.3},
    ])
    start = date(2026, 7, 24)
    base = {"starts_at": start, "review_at": start + timedelta(days=30),
            "expires_at": start + timedelta(days=90), "deltas": {"core": 0.02, "satellite": -0.02}}
    WealthService._validate_taa(saa, base)
    with pytest.raises(ValueError, match="必须为零"):
        WealthService._validate_taa(saa, {**base, "deltas": {"core": 0.02}})
    with pytest.raises(ValueError, match="安全层"):
        WealthService._validate_taa(saa, {**base, "deltas": {"safety": -0.01, "core": 0.01}})
    with pytest.raises(ValueError, match="超出SAA"):
        WealthService._validate_taa(saa, {**base, "deltas": {"core": 0.11, "satellite": -0.11}})
    with pytest.raises(ValueError, match="180天"):
        WealthService._validate_taa(saa, {**base, "expires_at": start + timedelta(days=181)})
    with pytest.raises(ValueError, match="非零"):
        WealthService._validate_taa(saa, {**base, "deltas": {"core": 0.0}})


def test_framework_versions_are_immutable_and_preview_is_read_only():
    service = (ROOT / "services/agent_platform/wealth.py").read_text()
    router = (ROOT / "routers/wealth.py").read_text()
    assert '"write_performed": False' in service
    assert '@router.post("/wealth-profile/framework-preview")' in router
    assert '@router.post("/wealth-profile/framework-versions")' in router
    assert '@router.put("/wealth-profile/framework-versions' not in router
    assert '@router.delete("/wealth-profile/framework-versions' not in router


def test_assignment_and_taa_ownership_hard_boundaries_are_explicit():
    service = (ROOT / "services/agent_platform/wealth.py").read_text()
    assert "指定金额超过当前价值" in service
    assert "短期目标“{goal.name}”不能依赖非流动资产" in service
    assert "必须保障目标“{goal.name}”不能使用进取层资金" in service
    assert 'MarketOpportunity.scope == "global"' in service
    assert "MarketOpportunity.user_id == self.user_id" in service
    assert 'values["evidence"] = _response_json(snapshot.evidence)' in service


def test_migration_038_is_additive_documented_and_keeps_existing_erc_engine():
    migration = (REPO / "migrations/versions/038_household_wealth_saa_taa.py").read_text()
    allocation = (ROOT / "services/agent_platform/allocation.py").read_text()
    assert 'revision = "038"' in migration
    assert 'down_revision = "037"' in migration
    assert "uq_household_members_one_self" in migration
    assert "COMMENT ON TABLE wealth_profiles" in migration
    assert "constrained_risk_parity" in allocation
    assert "optimization_method" not in migration
