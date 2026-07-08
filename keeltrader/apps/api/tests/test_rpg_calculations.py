"""RPG pure calculation regressions."""

from types import SimpleNamespace

from domain.rpg.calculations import (
    calculate_discipline,
    calculate_level,
    calculate_rank,
    calculate_risk_management,
)
from domain.rpg.models import Rank


def test_calculate_level_is_capped_and_has_minimum():
    assert calculate_level(-100) == 1
    assert calculate_level(0) == 1
    assert calculate_level(9_999_999) == 99


def test_calculate_rank_thresholds():
    assert calculate_rank(1) == Rank.BRONZE
    assert calculate_rank(20) == Rank.SILVER
    assert calculate_rank(40) == Rank.GOLD
    assert calculate_rank(60) == Rank.PLATINUM
    assert calculate_rank(80) == Rank.DIAMOND


def test_calculate_discipline_preserves_current_weighted_score_behavior():
    journals = [
        SimpleNamespace(stop_loss=90, followed_rules=True, rule_violations=[]),
        SimpleNamespace(stop_loss=None, followed_rules=False, rule_violations=["revenge_trade"]),
    ]

    assert calculate_discipline(journals) == 100


def test_calculate_risk_management_uses_rr_and_position_consistency():
    journals = [
        SimpleNamespace(risk_reward_ratio=2, position_size=100),
        SimpleNamespace(risk_reward_ratio=2, position_size=100),
        SimpleNamespace(risk_reward_ratio=2, position_size=100),
    ]

    assert calculate_risk_management(journals) == 100
