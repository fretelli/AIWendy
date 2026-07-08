"""Pure market data indicator calculations."""

from services.market_data_types import IndicatorPoint, PricePoint


def calculate_sma(data: list[PricePoint], period: int) -> list[IndicatorPoint]:
    """Calculate simple moving average values."""
    if period <= 0 or len(data) < period:
        return []

    return [
        {
            "time": data[i]["time"],
            "value": round(
                sum(point["close"] for point in data[i - period + 1 : i + 1])
                / period,
                2,
            ),
        }
        for i in range(period - 1, len(data))
    ]


def calculate_ema(data: list[PricePoint], period: int) -> list[IndicatorPoint]:
    """Calculate exponential moving average values."""
    if period <= 0 or len(data) < period:
        return []

    ema_data: list[IndicatorPoint] = []
    multiplier = 2 / (period + 1)

    sma = sum(point["close"] for point in data[:period]) / period
    ema_data.append({"time": data[period - 1]["time"], "value": round(sma, 2)})

    for i in range(period, len(data)):
        ema_value = (
            data[i]["close"] - ema_data[-1]["value"]
        ) * multiplier + ema_data[-1]["value"]
        ema_data.append({"time": data[i]["time"], "value": round(ema_value, 2)})

    return ema_data


def calculate_rsi(
    data: list[PricePoint], period: int = 14
) -> list[IndicatorPoint]:
    """Calculate relative strength index values."""
    if period <= 0 or len(data) < period + 1:
        return []

    rsi_data: list[IndicatorPoint] = []
    changes = [
        data[i]["close"] - data[i - 1]["close"] for i in range(1, len(data))
    ]

    gains = [change if change > 0 else 0 for change in changes[:period]]
    losses = [-change if change < 0 else 0 for change in changes[:period]]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period, len(changes)):
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        rsi_data.append({"time": data[i + 1]["time"], "value": round(rsi, 2)})

        current_gain = changes[i] if changes[i] > 0 else 0
        current_loss = -changes[i] if changes[i] < 0 else 0

        avg_gain = (avg_gain * (period - 1) + current_gain) / period
        avg_loss = (avg_loss * (period - 1) + current_loss) / period

    return rsi_data
