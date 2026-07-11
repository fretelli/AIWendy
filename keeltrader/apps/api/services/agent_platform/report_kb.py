"""Read-only report-kb client for AgentOS research context."""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib import error, parse, request

from config import get_settings


def _base_url() -> str | None:
    raw = (get_settings().report_kb_url or "").strip()
    return raw.rstrip("/") if raw else None


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


def _http_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    base = _base_url()
    if not base:
        return {"ok": False, "configured": False, "error": "REPORT_KB_URL is not configured"}

    data = None
    headers = {"accept": "application/json"}
    service_key = (get_settings().report_kb_service_key or "").strip()
    if service_key:
        headers["X-Report-KB-Service-Key"] = service_key
    if payload is not None:
        data = json.dumps(_json_safe(payload)).encode("utf-8")
        headers["content-type"] = "application/json"

    req = request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=get_settings().report_kb_timeout_seconds) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "configured": True, "error": str(exc)}


def _query_terms(query: str, companies: list[str] | None = None) -> list[str]:
    generic = {
        "投资",
        "研报",
        "盈利",
        "风险",
        "研究",
        "分析",
        "stock",
        "equity",
        "report",
        "research",
    }
    terms: list[str] = []
    for item in [*(companies or []), *query.replace("/", " ").replace("|", " ").split()]:
        value = str(item or "").strip()
        if not value or value.lower() in generic or value in generic:
            continue
        if value not in terms:
            terms.append(value)
        if "." in value:
            prefix = value.split(".", 1)[0]
            if prefix and prefix not in terms:
                terms.append(prefix)
        if len(terms) >= 8:
            break
    return terms


class ReportKBService:
    """Small async wrapper around report-kb's HTTP API."""

    async def health(self) -> dict[str, Any]:
        result = await asyncio.to_thread(_http_json, "GET", "/health")
        if result.get("status") == "ok":
            return {
                "configured": True,
                "reachable": True,
                "reports": result.get("reports"),
                "pg": result.get("pg"),
                "minio": result.get("minio"),
            }
        return {
            "configured": bool(_base_url()),
            "reachable": False,
            "reports": None,
            "error": str(result.get("error") or "unreachable")[:200],
        }

    async def search_reports(
        self,
        query: str,
        *,
        top_k: int = 5,
        companies: list[str] | None = None,
        granularity: str = "document",
        rerank: bool = True,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        limit = max(1, min(top_k, 20))
        payload = {
            "query": query.strip(),
            "top_k": limit,
            "doc_type": "research_report",
            "granularity": granularity,
            "rerank": rerank,
        }
        if companies:
            payload["companies"] = [item for item in companies if item]
        result = await asyncio.to_thread(_http_json, "POST", "/search", payload)
        rows = result.get("results") if isinstance(result, dict) else None
        if isinstance(rows, list) and rows:
            return [_normalize_search_hit(row) for row in rows]

        # Never substitute unrelated recent reports for missing company evidence.
        # An empty result is an explicit, auditable evidence shortage.
        return await self._search_recent_report_titles(query, limit=limit, companies=companies)

    async def recent_reports(self, *, limit: int = 5) -> list[dict[str, Any]]:
        path = "/reports/recent-candidates?" + parse.urlencode({
            "doc_type": "research_report",
            "limit": max(1, min(limit, 20)),
        })
        rows = await asyncio.to_thread(_http_json, "GET", path)
        if not isinstance(rows, list):
            return []
        return [_normalize_summary_hit(row, score=0, match_scopes=["recent"]) for row in rows]

    async def _search_recent_report_titles(
        self,
        query: str,
        *,
        limit: int,
        companies: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        terms = _query_terms(query, companies)
        if not terms:
            return []
        path = "/reports/recent-candidates?" + parse.urlencode({
            "doc_type": "research_report",
            "limit": 200,
        })
        rows = await asyncio.to_thread(_http_json, "GET", path)
        if not isinstance(rows, list):
            return []

        scored: list[tuple[int, dict[str, Any]]] = []
        lower_terms = [term.lower() for term in terms]
        for row in rows:
            haystack = " ".join(
                str(row.get(key) or "")
                for key in ("title", "summary", "broker", "report_date")
            ).lower()
            matched = [term for term in lower_terms if term and term in haystack]
            if not matched:
                continue
            title = str(row.get("title") or "").lower()
            score = 100 if any(term in title for term in matched) else 60
            score += min(len(matched) * 10, 30)
            scored.append((score, row))

        scored.sort(
            key=lambda item: (
                item[0],
                str(item[1].get("report_date") or ""),
                str(item[1].get("created_at") or ""),
            ),
            reverse=True,
        )
        return [
            _normalize_summary_hit(row, score=score, match_scopes=["title_or_summary"])
            for score, row in scored[:limit]
        ]


def _normalize_search_hit(row: dict[str, Any]) -> dict[str, Any]:
    content = row.get("content") or ""
    return {
        "report_id": str(row.get("report_id") or ""),
        "section_id": str(row.get("section_id") or ""),
        "title": row.get("report_title"),
        "broker": row.get("broker"),
        "report_date": row.get("report_date"),
        "created_at": row.get("created_at"),
        "doc_type": row.get("doc_type"),
        "section_type": row.get("section_type"),
        "granularity": row.get("granularity"),
        "page_number": row.get("page_number"),
        "score": row.get("score"),
        "excerpt": content[:1200],
        "metadata": row.get("metadata") or {},
    }


def _normalize_summary_hit(
    row: dict[str, Any],
    *,
    score: int | float,
    match_scopes: list[str],
) -> dict[str, Any]:
    metadata = row.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata = {
        **metadata,
        "match_scopes": match_scopes,
        "fallback": True,
    }
    return {
        "report_id": str(row.get("id") or row.get("report_id") or ""),
        "section_id": "",
        "title": row.get("title") or row.get("report_title"),
        "broker": row.get("broker"),
        "report_date": row.get("report_date"),
        "created_at": row.get("created_at"),
        "doc_type": row.get("doc_type"),
        "section_type": None,
        "granularity": "document",
        "page_number": None,
        "score": score,
        "excerpt": (row.get("summary") or row.get("title") or "")[:1200],
        "metadata": metadata,
    }
