"""Ordered development database schema section registry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncConnection

from .sections import (
    ensure_extensions_schema,
    ensure_auth_schema,
    ensure_notifications_schema,
    ensure_tenants_schema,
    ensure_projects_schema,
    ensure_files_schema,
    ensure_roundtable_schema,
    ensure_knowledge_schema,
    ensure_journals_schema,
    ensure_exchanges_schema,
    ensure_interventions_schema,
    ensure_patterns_schema,
    ensure_reports_schema,
    ensure_billing_schema,
)

SectionRunner = Callable[[AsyncConnection], Awaitable[None]]

SECTION_RUNNERS: tuple[SectionRunner, ...] = (
    ensure_extensions_schema,
    ensure_auth_schema,
    ensure_notifications_schema,
    ensure_tenants_schema,
    ensure_projects_schema,
    ensure_files_schema,
    ensure_roundtable_schema,
    ensure_knowledge_schema,
    ensure_journals_schema,
    ensure_exchanges_schema,
    ensure_interventions_schema,
    ensure_patterns_schema,
    ensure_reports_schema,
    ensure_billing_schema,
)
