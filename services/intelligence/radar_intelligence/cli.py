from __future__ import annotations

import asyncio
import logging

import click

from radar_domain.db import session_scope

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@click.group()
def intelligence() -> None:
    """Graphics Engine Radar intelligence pipeline."""


@intelligence.command("process")
@click.option("--limit", type=int, default=None, help="max new RawItems to process")
def process(limit: int | None) -> None:
    """Rule filter + candidate detection + event pipeline over pending RawItems."""
    from radar_intelligence.pipeline import run_intelligence

    async def _go():
        with session_scope() as session:
            stats = await run_intelligence(session, limit=limit)
        click.echo(stats["filter"])
        click.echo(f"processed={stats['processed']} outcomes={stats['outcomes']}")

    asyncio.run(_go())


@intelligence.command("trends")
def trends() -> None:
    """Recompute topic trend snapshots."""
    from radar_intelligence.trend import topic_latest_trends, update_trends

    with session_scope() as session:
        n = update_trends(session)
        rows = topic_latest_trends(session)
    click.echo(f"updated {n} snapshots")
    for row in rows[:15]:
        click.echo(f"{row['topic_slug']:32s} {row['state']:14s} "
                   f"events30d={row['event_count_30d']} important={row['important_event_count_30d']} "
                   f"objects={row['unique_object_count_30d']}")


@intelligence.command("digest")
@click.option("--kind", type=click.Choice(["daily", "weekly", "monthly"]), default="daily")
def digest(kind: str) -> None:
    """Generate a digest for the given window."""
    from radar_intelligence.digest import generate_digest

    with session_scope() as session:
        out = generate_digest(session, kind)
    click.echo(out or f"no events in {kind} window")


@intelligence.command("select")
def select_cmd() -> None:
    """Show homepage selection (rule-based, no fixed count)."""
    from radar_intelligence.digest import select_for_homepage

    with session_scope() as session:
        events = select_for_homepage(session)
    click.echo(f"selected {len(events)} events")
    for e in events:
        click.echo(f"[{e.impact_level:8s}] ({e.change_signal}) {e.title[:90]}")


@intelligence.command("metrics")
def metrics() -> None:
    """MVP acceptance metrics (spec §30)."""
    from sqlalchemy import func

    from radar_domain.models import AIExecution, Event, EventSource, RawItem

    with session_scope() as session:
        raw_total = session.query(func.count(RawItem.id)).scalar()
        ignored = session.query(func.count(RawItem.id)).filter(
            RawItem.filter_status == "ignored").scalar()
        candidates = session.query(func.count(RawItem.id)).filter(
            RawItem.filter_status == "candidate").scalar()
        event_total = session.query(func.count(Event.id)).scalar()
        selected = session.query(func.count(Event.id)).filter(
            Event.impact_level.in_(("High", "Critical"))).scalar()
        merged_raws = session.query(func.count(EventSource.id)).scalar()
        events_with_sources = session.query(func.count(func.distinct(EventSource.event_id))).scalar()
        official_events = (
            session.query(func.count(func.distinct(EventSource.event_id)))
            .join(RawItem, EventSource.raw_item_id == RawItem.id)
            .filter(RawItem.source_id.in_(
                session.query(RawItem.source_id).filter(RawItem.source_id.isnot(None))))
            .scalar()
        )
        # official-source events: event has a source whose role in (primary, official)
        from radar_domain.models import Source
        official_events = (
            session.query(func.count(func.distinct(EventSource.event_id)))
            .join(RawItem, EventSource.raw_item_id == RawItem.id)
            .join(Source, RawItem.source_id == Source.id)
            .filter(Source.type.in_(("github_release", "release_notes", "spec_registry",
                                     "official_blog", "github_pr")))
            .scalar()
        )
        ai_calls = session.query(func.count(AIExecution.id)).scalar()
    click.echo(f"RawItem total:        {raw_total}")
    click.echo(f"Ignored:              {ignored}")
    click.echo(f"Candidates:           {candidates}")
    click.echo(f"Events:               {event_total}")
    click.echo(f"Selected (High/High+): {selected}")
    click.echo(f"Evidence links (merges): {merged_raws}")
    click.echo(f"Events with official source: {official_events}"
               f" ({(official_events / events_with_sources * 100 if events_with_sources else 0):.0f}%)")
    click.echo(f"AI executions recorded: {ai_calls}")
