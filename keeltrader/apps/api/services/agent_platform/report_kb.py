"""Read-only report-kb client for AgentOS research context."""

from __future__ import annotations

import asyncio
import json
import re
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
        "基本面",
        "业绩",
        "估值",
        "财务",
        "证券",
        "股票",
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


def _company_identifiers(companies: list[str] | None) -> list[str]:
    identifiers: list[str] = []
    for item in companies or []:
        value = str(item or "").strip().lower()
        if not value:
            continue
        variants = (value, re.sub(r"\.(?:sh|sz|bj|hk)$", "", value))
        for variant in variants:
            if variant and variant not in identifiers:
                identifiers.append(variant)
    return identifiers


def _contains_identifier(text: str, identifier: str) -> bool:
    haystack = str(text or "").lower()
    needle = str(identifier or "").lower()
    if not haystack or not needle:
        return False
    if re.fullmatch(r"\d{4,8}", needle):
        return re.search(rf"(?<![0-9a-z]){re.escape(needle)}(?![0-9a-z])", haystack) is not None
    if re.fullmatch(r"[a-z][a-z0-9.+-]*", needle):
        return re.search(rf"(?<![0-9a-z]){re.escape(needle)}(?![0-9a-z])", haystack) is not None
    return len(needle) >= 2 and needle in haystack


def _structured_company_identifiers(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("company_names", "primary_company_name", "companies"):
        raw = metadata.get(key)
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            if isinstance(item, dict):
                candidates = [item.get("name"), item.get("name_cn"), item.get("ticker")]
            else:
                candidates = [item]
            for candidate in candidates:
                values.extend(_company_identifiers([str(candidate or "")]))
    if metadata.get("_search_company_filter_verified") is True:
        raw_verified = metadata.get("_search_company_identifiers")
        if isinstance(raw_verified, list):
            values.extend(_company_identifiers([str(item or "") for item in raw_verified]))
    return list(dict.fromkeys(values))


def _report_matches_company(report: dict[str, Any], companies: list[str] | None) -> bool:
    requested = _company_identifiers(companies)
    if not requested:
        return True
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    structured = _structured_company_identifiers(metadata)
    if set(requested) & set(structured):
        return True
    text = " ".join(str(report.get(key) or "") for key in ("title", "excerpt"))
    return any(_contains_identifier(text, identifier) for identifier in requested)


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
            normalized = [_normalize_search_hit(row) for row in rows]
            accepted = [row for row in normalized if _report_matches_company(row, companies)]
            for row in accepted:
                row["company_match_verified"] = True
            return accepted

        # Company evidence must come from a locatable search hit. Never turn a
        # generic title/summary match into company evidence.
        if companies:
            return []
        return await self._search_recent_report_titles(query, limit=limit, companies=companies)

    async def company_report_candidates(
        self,
        companies: list[str],
        *,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        identifiers = [item for item in companies if str(item or "").strip()]
        if not identifiers:
            return []
        query_items: list[tuple[str, Any]] = [
            ("doc_type", "research_report"),
            ("limit", max(1, min(limit, 200))),
            ("include_incomplete", "true"),
        ]
        query_items.extend(("companies", item) for item in identifiers)
        path = "/reports/recent-candidates?" + parse.urlencode(query_items)
        rows = await asyncio.to_thread(_http_json, "GET", path)
        if not isinstance(rows, list):
            return []
        normalized = [_normalize_summary_hit(row, score=0, match_scopes=["structured_company"]) for row in rows]
        accepted = [row for row in normalized if _report_matches_company(row, identifiers)]
        for row in accepted:
            row["company_match_verified"] = True
        return accepted

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
        "company_names": row.get("company_names") or metadata.get("company_names") or [],
        "primary_company_name": row.get("primary_company_name") or metadata.get("primary_company_name"),
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
        "sections_count": row.get("sections_count"),
        "ingest_status": row.get("ingest_status"),
    }
