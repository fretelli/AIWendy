"""Durable shareholder watch scans and disclosure change records."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.logging import get_logger
from domain.agent_platform.models import (
    AgentBackgroundJob,
    AgentHolderEvent,
    AgentHolderWatchlist,
)
from services.agent_platform.tushare import TushareReadService

logger = get_logger(__name__)


def normalize_holder_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").strip()
    return re.sub(r"\s+", " ", normalized)


def holder_names(watch: AgentHolderWatchlist) -> list[str]:
    values = [watch.holder_name, *(watch.aliases or [])]
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        name = normalize_holder_name(str(value))
        if name and name not in seen:
            result.append(name)
            seen.add(name)
    return result


async def enqueue_holder_scan(
    session: AsyncSession,
    user_id,
    watch_id,
    *,
    initial: bool = False,
) -> None:
    await session.execute(pg_insert(AgentBackgroundJob).values(
        id=uuid4(), user_id=user_id, kind="holder_scan",
        entity_key=f"{user_id}:{watch_id}", payload={"watch_id": str(watch_id), "initial": initial},
        status="queued", available_at=datetime.now(UTC), attempts=0, max_attempts=3,
    ).on_conflict_do_nothing())


async def _claim_holder_job(session: AsyncSession, worker_id: str) -> AgentBackgroundJob | None:
    now = datetime.now(UTC)
    item = (await session.execute(select(AgentBackgroundJob).where(
        AgentBackgroundJob.kind == "holder_scan",
        AgentBackgroundJob.status.in_({"queued", "retry", "running"}),
        AgentBackgroundJob.available_at <= now,
        (AgentBackgroundJob.lease_expires_at.is_(None) | (AgentBackgroundJob.lease_expires_at < now)),
    ).order_by(AgentBackgroundJob.created_at).with_for_update(skip_locked=True).limit(1))).scalar_one_or_none()
    if item:
        item.status = "running"
        item.attempts += 1
        item.lease_owner = worker_id
        item.lease_expires_at = now.replace(microsecond=0) + timedelta(minutes=10)
        await session.flush()
    return item


async def scan_holder_watch(
    session: AsyncSession,
    watch: AgentHolderWatchlist,
    *,
    initial: bool = False,
) -> int:
    service = TushareReadService(session)
    watermark = await service.holder_source_watermark()
    page_size = 1000
    offset = 0
    inserted = 0
    now = datetime.now(UTC)
    # The inbox is operational history, not the full query archive. The live history
    # endpoint remains unbounded and paginated back to 2020.
    min_end_date = f"{now.year - 1}0101"

    while True:
        result = await service.holder_history(
            holder_names(watch), watch.holder_type,
            limit=page_size, offset=offset, min_end_date=min_end_date,
            include_price_estimates=False,
        )
        if not result["source_available"]:
            raise RuntimeError("top10_floatholders source is unavailable")
        rows = result["items"]
        for row in rows:
            event_key = hashlib.sha256(
                f"{watch.id}|{row['ts_code']}|{row['end_date']}".encode("utf-8")
            ).hexdigest()
            values = {
                "matched_names": row.get("matched_names") or [],
                "hold_amount": row.get("hold_amount"),
                "hold_ratio": row.get("hold_ratio"),
                "hold_float_ratio": row.get("hold_float_ratio"),
                "hold_change": row.get("hold_change"),
                "previous_hold_amount": row.get("previous_hold_amount"),
                "previous_hold_ratio": row.get("previous_hold_ratio"),
                "previous_hold_float_ratio": row.get("previous_hold_float_ratio"),
            }
            statement = pg_insert(AgentHolderEvent).values(
                id=uuid4(), user_id=watch.user_id, watch_id=watch.id, event_key=event_key,
                ts_code=row["ts_code"], company_name=row.get("company_name"),
                holder_name=watch.holder_name, holder_type=watch.holder_type,
                event_type=row["event_type"], end_date=row["end_date"], ann_date=row.get("ann_date"),
                previous_end_date=row.get("previous_end_date"), values=values,
                read_at=now if initial else None, detected_at=now,
            ).on_conflict_do_update(
                index_elements=["watch_id", "ts_code", "end_date"],
                set_={
                    "company_name": row.get("company_name"),
                    "event_type": row["event_type"],
                    "ann_date": row.get("ann_date"),
                    "previous_end_date": row.get("previous_end_date"),
                    "values": values,
                    "updated_at": now,
                },
            )
            await session.execute(statement)
            inserted += 1
        offset += len(rows)
        if not rows or offset >= int(result["total"]):
            break

    watch.last_scanned_at = now
    watch.last_source_watermark = watermark
    return inserted


async def holder_worker_loop() -> None:
    worker_id = f"holder:{os.uname().nodename}:{os.getpid()}"
    while True:
        async with async_session() as session:
            async with session.begin():
                item = await _claim_holder_job(session, worker_id)
            if not item:
                await asyncio.sleep(1)
                continue
            job_id = item.id
            try:
                watch = await session.get(AgentHolderWatchlist, UUID(str(item.payload["watch_id"])))
                if watch and watch.enabled:
                    await scan_holder_watch(session, watch, initial=bool(item.payload.get("initial")))
                item.status = "completed"
                item.finished_at = datetime.now(UTC)
                item.lease_owner = None
                item.lease_expires_at = None
                await session.commit()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await session.rollback()
                async with session.begin():
                    failed = await session.get(AgentBackgroundJob, job_id, with_for_update=True)
                    if failed is None:
                        logger.error("holder_scan_job_missing", job_id=str(job_id))
                        continue
                    failed.last_error = str(exc)[:2000]
                    failed.lease_owner = None
                    failed.lease_expires_at = None
                    if failed.attempts < failed.max_attempts:
                        failed.status = "retry"
                        failed.available_at = datetime.now(UTC) + timedelta(seconds=2 ** failed.attempts * 15)
                    else:
                        failed.status = "failed"
                        failed.finished_at = datetime.now(UTC)
                logger.exception("holder_scan_failed", job_id=str(job_id), error=str(exc))


async def holder_scheduler_loop() -> None:
    """Refresh enabled holder inboxes once daily after upstream incremental sync."""
    last_date = None
    while True:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        if (now.hour, now.minute) >= (0, 45) and last_date != now.date():
            async with async_session() as session:
                watches = (await session.execute(select(AgentHolderWatchlist).where(
                    AgentHolderWatchlist.enabled.is_(True)
                ))).scalars().all()
                for watch in watches:
                    await enqueue_holder_scan(session, watch.user_id, watch.id)
                await session.commit()
            last_date = now.date()
        await asyncio.sleep(30)
