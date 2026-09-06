from __future__ import annotations

import asyncio
import logging

import click

from radar_domain.config_loader import sync_all
from radar_domain.db import session_scope
from radar_domain.settings import REPO_ROOT, get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@click.group()
def collector() -> None:
    """Graphics Engine Radar collector."""


@collector.command("sync-config")
def sync_config() -> None:
    """Load config/{objects,topics,sources} into the database (idempotent)."""
    with session_scope() as session:
        stats = sync_all(session, get_settings().config_dir)
    click.echo(stats)


@collector.command("run")
@click.option("--limit", type=int, default=None, help="max sources to poll this run")
@click.option("--loop", is_flag=True, help="keep polling forever")
@click.option("--interval", type=int, default=60, help="seconds between polls in loop mode")
def run(limit: int | None, loop: bool, interval: int) -> None:
    """Poll due sources (or everything once with --limit 0? use `run-all`)."""
    from radar_collector.runner import collect_due_sources

    async def _once() -> None:
        with session_scope() as session:
            results = await collect_due_sources(session, limit=limit)
        ok = sum(1 for r in results if r.get("ok"))
        click.echo(f"polled {len(results)} sources: {ok} ok, "
                   f"{sum(r.get('inserted', 0) for r in results)} new raw items")

    if loop:
        asyncio.run(_loop(_once, interval))
    else:
        asyncio.run(_once())


@collector.command("run-all")
def run_all() -> None:
    """Force-collect every enabled source once."""
    from radar_collector.runner import collect_all

    async def _go() -> None:
        with session_scope() as session:
            results = await collect_all(session)
        ok = sum(1 for r in results if r.get("ok"))
        click.echo(f"collected {len(results)} sources: {ok} ok, "
                   f"{sum(r.get('inserted', 0) for r in results)} new raw items")

    asyncio.run(_go())


async def _loop(once, interval: int) -> None:
    import time

    while True:
        await once()
        time.sleep(interval)
