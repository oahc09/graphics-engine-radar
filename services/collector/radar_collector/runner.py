"""Collector runner (spec §19/§34): dispatch adapters, persist RawItems
idempotently, and keep per-source cursor/observability state.

One source failing must not affect others.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from radar_adapters import content_hash, get_adapter
from radar_domain.models import RawItem, Source
from radar_domain.settings import get_settings

log = logging.getLogger("collector")


def _parse_ts(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def persist_items(session: Session, source: Source, drafts) -> tuple[int, int]:
    """Insert drafts, skipping duplicates by (source_id, external_id), then
    canonical_url, then content_hash (spec §35). Returns (inserted, skipped)."""
    inserted = skipped = 0
    for draft in drafts:
        existing = session.scalar(
            select(RawItem).where(
                RawItem.source_id == source.id,
                RawItem.external_id == draft.external_id,
            )
        )
        if existing is not None:
            skipped += 1
            continue
        canon = draft.canonical_url or draft.url
        if canon:
            by_url = session.scalar(
                select(RawItem).where(RawItem.canonical_url == canon)
            )
            if by_url is not None:
                skipped += 1
                continue
        chash = content_hash(f"{draft.title}\n{draft.content}")
        by_hash = session.scalar(select(RawItem).where(RawItem.content_hash == chash))
        if by_hash is not None:
            skipped += 1
            continue
        session.add(RawItem(
            source_id=source.id,
            external_id=draft.external_id,
            url=draft.url,
            canonical_url=canon,
            title=draft.title,
            content=draft.content,
            author=draft.author,
            published_at=_parse_ts(draft.published_at),
            content_hash=chash,
            raw_payload=draft.raw_payload or {},
        ))
        inserted += 1
    session.flush()
    return inserted, skipped


async def collect_source(session: Session, source: Source) -> dict:
    """Collect one source. Updates cursor, success/error state, next poll."""
    result: dict = {"source_id": str(source.id), "object": source.object.slug,
                    "adapter": source.adapter, "inserted": 0, "skipped": 0,
                    "ok": False}
    try:
        adapter = get_adapter(source.adapter)
        fetch = await adapter.fetch(source, source.last_cursor)
        inserted, skipped = persist_items(session, source, fetch.items)
        source.last_cursor = fetch.next_cursor or source.last_cursor
        now = datetime.now(timezone.utc)
        source.last_success_at = now
        source.last_error = None
        source.next_poll_at = now + timedelta(minutes=source.poll_interval_minutes)
        session.commit()
        result.update(ok=True, inserted=inserted, skipped=skipped,
                      cursor=fetch.next_cursor)
        log.info("source %s/%s: +%d (%d skipped)", source.object.slug,
                 source.adapter, inserted, skipped)
    except Exception as exc:  # one source failing must not affect others
        session.rollback()
        now = datetime.now(timezone.utc)
        source.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        source.next_poll_at = now + timedelta(minutes=max(source.poll_interval_minutes, 15))
        session.commit()
        result["error"] = result["last_error"] = source.last_error
        log.warning("source %s/%s failed: %s", source.object.slug,
                    source.adapter, source.last_error)
    return result


async def collect_due_sources(session: Session, limit: int | None = None) -> list[dict]:
    now = datetime.now(timezone.utc)
    q = (
        session.query(Source)
        .filter(Source.enabled.is_(True))
        .filter(
            (Source.next_poll_at.is_(None)) | (Source.next_poll_at <= now)
        )
        .order_by(Source.next_poll_at.isnot(None), Source.next_poll_at)
    )
    if limit:
        q = q.limit(limit)
    sources = q.all()
    return [await collect_source(session, s) for s in sources]


async def collect_all(session: Session) -> list[dict]:
    """Collect every enabled source once, regardless of next_poll_at."""
    sources = session.query(Source).filter(Source.enabled.is_(True)).all()
    return [await collect_source(session, s) for s in sources]
