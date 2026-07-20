"""Deterministic calculations and factual language for the market-capital snapshot."""
from __future__ import annotations
from typing import Any


def market_day(rows: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = [float(row.get("amount") or 0) * 1000 for row in rows]
    returns = [float(row["pct_chg"]) for row in rows if row.get("pct_chg") is not None]
    total, ordered = sum(amounts), sorted(amounts, reverse=True)
    return {"turnover_cny": total, "advances": sum(v > 0 for v in returns),
            "declines": sum(v < 0 for v in returns), "flat": sum(v == 0 for v in returns),
            "advance_ratio": sum(v > 0 for v in returns) / len(returns) if returns else None,
            "top20_turnover_share": sum(ordered[:20]) / total if total else None,
            "top50_turnover_share": sum(ordered[:50]) / total if total else None}


def financing_net(purchases: float | None, repayments: float | None) -> float | None:
    return None if purchases is None or repayments is None else float(purchases) - float(repayments)


def etf_flow(share_now_10k: float | None, share_previous_10k: float | None, nav: float | None) -> float | None:
    return None if None in (share_now_10k, share_previous_10k, nav) else (float(share_now_10k) - float(share_previous_10k)) * 10_000 * float(nav)


def factual_interpretations(snapshot: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    breadth = snapshot.get("breadth") or {}
    if all(breadth.get(key) is not None for key in ("advances", "declines", "flat")):
        lines.append(f"当日上涨{breadth['advances']}家、下跌{breadth['declines']}家、平盘{breadth['flat']}家。")
    leverage = snapshot.get("leverage") or {}
    if leverage.get("available") and leverage.get("daily_net_financing_cny") is not None:
        value = leverage["daily_net_financing_cny"]
        lines.append(f"当日{'融资净买入' if value >= 0 else '融资净偿还'}{abs(value) / 1e8:.1f}亿元，覆盖{leverage.get('coverage_label', '已披露市场')}。")
    if not (snapshot.get("flow_proxy") or {}).get("available"):
        lines.append("供应商主力资金代理口径当前不可用，未使用成交额替代。")
    return lines
