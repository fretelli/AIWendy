"""Market data indicator calculation regressions."""

from services.market_data_indicators import calculate_ema, calculate_rsi, calculate_sma
from services.market_data_types import PricePoint


def make_points(closes: list[float]) -> list[PricePoint]:
    return [
        {
            "time": f"2026-01-{index + 1:02d}",
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1000 + index,
        }
        for index, close in enumerate(closes)
    ]


def test_indicators_handle_empty_or_short_inputs():
    assert calculate_sma([], 3) == []
    assert calculate_ema(make_points([1, 2]), 3) == []
    assert calculate_rsi(make_points([1, 2, 3]), 3) == []
    assert calculate_sma(make_points([1, 2, 3]), 0) == []
    assert calculate_ema(make_points([1, 2, 3]), 0) == []
    assert calculate_rsi(make_points([1, 2, 3]), 0) == []


def test_calculate_sma_uses_rolling_window():
    assert calculate_sma(make_points([10, 20, 30, 40]), 3) == [
        {"time": "2026-01-03", "value": 20},
        {"time": "2026-01-04", "value": 30},
    ]


def test_calculate_ema_preserves_existing_rounding_behavior():
    assert calculate_ema(make_points([10, 20, 30, 40]), 3) == [
        {"time": "2026-01-03", "value": 20},
        {"time": "2026-01-04", "value": 30},
    ]


def test_calculate_rsi_returns_smoothed_values():
    result = calculate_rsi(make_points([10, 12, 11, 14, 13, 15]), 3)

    assert result == [
        {"time": "2026-01-05", "value": 83.33},
        {"time": "2026-01-06", "value": 66.67},
    ]
