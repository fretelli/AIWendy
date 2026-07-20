"""Deterministic calculations and factual language for the market-capital snapshot."""
from __future__ import annotations
from statistics import median
from typing import Any


def pct_change(value: float | None, base: float | None) -> float | None:
    return None if value is None or base in (None, 0) else (float(value) / float(base) - 1) * 100


def market_day(rows: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = [float(row.get("amount") or 0) * 1000 for row in rows]
    returns = [float(row["pct_chg"]) for row in rows if row.get("pct_chg") is not None]
    total, ordered = sum(amounts), sorted(amounts, reverse=True)
    return {"turnover_cny": total, "advances": sum(v > 0 for v in returns),
            "declines": sum(v < 0 for v in returns), "flat": sum(v == 0 for v in returns),
            "advance_ratio": sum(v > 0 for v in returns) / len(returns) if returns else None,
            "median_return_pct": median(returns) if returns else None,
            "top20_turnover_share": sum(ordered[:20]) / total if total else None,
            "top50_turnover_share": sum(ordered[:50]) / total if total else None}


def financing_net(purchases: float | None, repayments: float | None) -> float | None:
    return None if purchases is None or repayments is None else float(purchases) - float(repayments)


def etf_flow(share_now_10k: float | None, share_previous_10k: float | None, nav: float | None) -> float | None:
    return None if None in (share_now_10k, share_previous_10k, nav) else (float(share_now_10k) - float(share_previous_10k)) * 10_000 * float(nav)


def factual_interpretations(snapshot: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    liquidity, breadth = snapshot.get("liquidity") or {}, snapshot.get("breadth") or {}
    vs20, advances = liquidity.get("vs_20d_pct"), breadth.get("advance_ratio")
    if vs20 is not None:
        text = f"成交额较20日均值{'高' if vs20 >= 0 else '低'}{abs(vs20):.1f}%"
        if advances is not None:
            text += f"，上涨家数占比为{advances * 100:.1f}%"
        lines.append(text + "。")
    leverage = snapshot.get("leverage") or {}
    if leverage.get("available") and leverage.get("daily_net_financing_cny") is not None:
        value = leverage["daily_net_financing_cny"]
        lines.append(f"当日{'融资净买入' if value >= 0 else '融资净偿还'}{abs(value) / 1e8:.1f}亿元，覆盖{leverage.get('coverage_label', '已披露市场')}。")
    if not (snapshot.get("flow_proxy") or {}).get("available"):
        lines.append("供应商主力资金代理口径当前不可用，未使用成交额替代。")
    return lines
