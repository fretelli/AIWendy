"""Read the deployment-owned Structured Data capability manifest."""
from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any

from config import get_settings

_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_lock = Lock()
_cached: tuple[int, dict[str, Any]] | None = None

# Compatibility-only bootstrap list. Production reads the mounted manifest.
BOOTSTRAP_QUERY_TABLES = frozenset("""stock_basic stock_daily stock_daily_adj stock_weekly stock_monthly fina_indicator
income balancesheet cashflow dividend trade_cal index_basic index_global fund_basic fund_company fund_manager fund_nav
fund_daily fund_share fund_portfolio fund_div margin margin_detail stk_limit moneyflow_mkt_dc cn_cpi cn_ppi cn_pmi cn_gdp
shibor lpr top10_floatholders fut_basic fut_daily fut_mapping opt_basic opt_daily opt_series_daily index_daily cn_m
sf_month us_tycr us_trycr repo_daily shibor_quote cb_basic cb_daily option_underlying_map option_analytics_daily
allocation_series_catalog allocation_series_monthly allocation_instrument_catalog hk_basic hk_income hk_balancesheet
hk_cashflow hk_fina_indicator fx_daily fx_obasic sz_daily_info""".split())


def _unavailable(reason: str) -> dict[str, Any]:
    return {"available": False, "version": "unavailable", "generated_at": None, "source": "tushare-structured-data",
            "capabilities": [], "unavailable_reason": reason, "synthetic_substitution": False}


def read_capability_manifest() -> dict[str, Any]:
    global _cached
    path = Path(get_settings().market_capability_manifest_path)
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return _unavailable("结构化数据能力清单不可用；不扩大查询白名单或合成缺失数据。")
    with _lock:
        if _cached and _cached[0] == mtime:
            return _cached[1]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return _unavailable("结构化数据能力清单损坏；查询保持最小兼容白名单。")
        capabilities = payload.get("capabilities") if isinstance(payload, dict) else None
        if not isinstance(capabilities, list):
            return _unavailable("结构化数据能力清单格式不受支持。")
        payload["available"] = True
        _cached = (mtime, payload)
        return payload


def queryable_tables() -> frozenset[str]:
    manifest = read_capability_manifest()
    tables = {str(item.get("table")) for item in manifest.get("capabilities", [])
              if item.get("physical") and item.get("available") and item.get("exposure") in {"typed_api", "agent_query"}
              and item.get("table") and _IDENT.match(str(item.get("table")))}
    return frozenset(tables) if tables else BOOTSTRAP_QUERY_TABLES


def physical_tables() -> frozenset[str]:
    manifest = read_capability_manifest()
    tables = {str(item.get("table")) for item in manifest.get("capabilities", [])
              if item.get("physical") and item.get("available") and item.get("table")
              and _IDENT.match(str(item.get("table")))}
    return frozenset(tables) if tables else BOOTSTRAP_QUERY_TABLES


def capability_version() -> str:
    return str(read_capability_manifest().get("version") or "unavailable")
