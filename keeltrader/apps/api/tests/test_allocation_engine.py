import numpy as np

from services.agent_platform.allocation import (
    apply_tactical_tilts,
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


def test_tactical_tilts_must_be_self_financing_and_keep_risk_limits():
    returns = sample_returns()
    base = policy_from_returns(capital=1_000_000, reserve=300_000, max_drawdown=0.2,
        sleeves=["china_equity", "global_equity", "china_bond", "global_bond", "gold"], returns=returns)
    tilted = apply_tactical_tilts(base, [
        {"sleeve_key": "china_equity", "weight_delta": 0.01},
        {"sleeve_key": "cny_cash", "weight_delta": -0.01},
    ], returns=returns, sleeves=["china_equity", "global_equity", "china_bond", "global_bond", "gold"],
        max_drawdown=0.2, max_leverage=1)
    assert np.isclose(sum(tilted["weights"].values()), 1)
    assert tilted["risk_summary"]["tactical_tilt_count"] == 2
