import numpy as np
import pytest

from services.agent_platform.allocation import (
    constrained_risk_parity,
    policy_from_returns,
    scaled_currency_exposure,
    stable_hash,
)


def sample_returns(months: int = 180) -> np.ndarray:
    generator = np.random.default_rng(42)
    common = generator.normal(0.004, 0.025, size=(months, 1))
    noise = generator.normal(0, 0.02, size=(months, 5))
    scales = np.asarray([1.2, 1.1, 0.35, 0.4, 0.7])
    return common * scales + noise * scales


def test_equal_risk_engine_is_deterministic_and_respects_bounds():
    returns = sample_returns()
    first = constrained_risk_parity(returns)
    second = constrained_risk_parity(returns)
    assert np.allclose(first[0], second[0])
    assert np.isclose(first[0].sum(), 1)
    assert np.all(first[0] >= 0)
    assert np.all(first[0] <= 0.55 + 1e-9)
    assert np.isclose(first[1].sum(), 1)


def test_policy_reserves_cash_and_scales_risk_to_drawdown_limit():
    result = policy_from_returns(
        capital=1_000_000,
        reserve=200_000,
        max_drawdown=0.12,
        sleeves=["china_equity", "global_equity", "china_bond", "global_bond", "gold"],
        returns=sample_returns(), max_leverage=0.6,
    )
    assert result["status"] == "feasible"
    assert np.isclose(sum(result["weights"].values()), 1)
    assert result["weights"]["cny_cash"] >= 0.20 - 1e-9
    assert result["risk_summary"]["worst_stress_return"] >= -0.1200001
    assert result["risk_summary"]["gross_underlying_exposure"] <= 0.6 + 1e-9


def test_policy_reports_infeasible_cash_needs_without_relaxing_them():
    result = policy_from_returns(
        capital=100,
        reserve=101,
        max_drawdown=0.2,
        sleeves=["china_equity", "global_equity", "china_bond", "global_bond", "gold"],
        returns=sample_returns(),
    )
    assert result["status"] == "infeasible"
    assert "超过总资金" in result["reasons"][0]


def test_content_hash_ignores_dictionary_order():
    assert stable_hash({"a": 1, "b": [2]}) == stable_hash({"b": [2], "a": 1})


def test_currency_exposure_is_scaled_by_portfolio_weight():
    assert scaled_currency_exposure({"USD": 1}, 0.25) == {"USD": 0.25}
    assert scaled_currency_exposure({"USD": 0.6, "JPY": 0.4}, 0.5) == {"USD": 0.3, "JPY": 0.2}
    assert scaled_currency_exposure(None, 0.5) == {}


@pytest.mark.parametrize("methodology,views", [
    ("risk_parity", {}),
    ("all_weather", {}),
    ("lifecycle", {}),
    ("core_satellite", {"as_of": "2026-07-31", "tilts": {"china_equity": 0.03, "global_bond": -0.03}}),
    ("black_litterman", {"as_of": "2026-07-31",
        "market_weights": {"china_equity": .2, "global_equity": .25, "china_bond": .2, "global_bond": .25, "gold": .1},
        "expected_return_adjustment": {"china_equity": .01, "global_bond": -.005}}),
])
def test_all_five_methodologies_are_deterministic_and_constrained(methodology, views):
    kwargs = dict(capital=1_000_000, reserve=100_000, max_drawdown=.2,
        sleeves=["china_equity", "global_equity", "china_bond", "global_bond", "gold"],
        returns=sample_returns(), methodology_key=methodology, horizon_months=180, view_snapshot=views)
    first, second = policy_from_returns(**kwargs), policy_from_returns(**kwargs)
    assert first["status"] == "feasible"
    assert first["weights"] == second["weights"]
    assert np.isclose(sum(first["weights"].values()), 1)
    assert max(value for key, value in first["weights"].items() if key != "cny_cash") <= .55 + 1e-9
    assert first["methodology"]["key"] == methodology


@pytest.mark.parametrize("methodology", ["black_litterman", "core_satellite"])
def test_view_dependent_methods_fail_instead_of_generating_example_weights(methodology):
    with pytest.raises(ValueError):
        policy_from_returns(capital=1_000_000, reserve=0, max_drawdown=.2,
            sleeves=["china_equity", "global_equity", "china_bond", "global_bond", "gold"],
            returns=sample_returns(), methodology_key=methodology, view_snapshot={})
