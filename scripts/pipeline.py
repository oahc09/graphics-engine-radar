#!/usr/bin/env python3
"""Single production pipeline entrypoint.

Runs collect -> intelligence -> trends -> digests exactly once, propagates the
first failing stage as a non-zero process exit, and uses a PostgreSQL advisory
lock so manual and scheduled runs cannot overlap across processes/hosts.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PIPELINE_LOCK_KEY = 0x47524144  # stable "GRAD" advisory-lock key


@dataclass(frozen=True)
class Stage:
    name: str
    runner: Callable[[], None]


def _invoke_click(group, args: list[str]) -> None:
    """Invoke Click without standalone SystemExit handling.

    Click errors/Abort propagate to the caller; successful commands return and
    allow the next pipeline stage to execute.
    """
    result = group.main(args=args, standalone_mode=False)
    if isinstance(result, int) and result != 0:
        from click.exceptions import Exit
        raise Exit(result)


def default_stages() -> list[Stage]:
    from radar_collector.cli import collector
    from radar_intelligence.cli import intelligence
    return [
        Stage("collect", lambda: _invoke_click(collector, ["run-all"])),
        Stage("intelligence", lambda: _invoke_click(intelligence, ["process"])),
        Stage("trends", lambda: _invoke_click(intelligence, ["trends"])),
        Stage("digest_daily", lambda: _invoke_click(intelligence, ["digest", "--kind", "daily"])),
        Stage("digest_weekly", lambda: _invoke_click(intelligence, ["digest", "--kind", "weekly"])),
        Stage("digest_monthly", lambda: _invoke_click(intelligence, ["digest", "--kind", "monthly"])),
    ]


def _maybe_load_github_token() -> None:
    if os.environ.get("GITHUB_TOKEN"):
        return
    try:
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if token:
            os.environ["GITHUB_TOKEN"] = token
            print("[github] using gh auth token")
            return
    except Exception:
        pass
    print("[github] no GITHUB_TOKEN / gh CLI - anonymous rate limits apply")


def _db_tracking_available():
    try:
        from sqlalchemy import text
        from radar_domain.db import engine
        from radar_domain.pipeline_state import PipelineRun
        return engine, text, PipelineRun
    except Exception:
        return None


def run_pipeline(stages: Iterable[Stage] | None = None, *, use_db_lock: bool = True) -> int:
    run_id = uuid.uuid4().hex
    started = datetime.now(timezone.utc)
    print(f"pipeline run_id={run_id} started_at={started.isoformat()}")
    _maybe_load_github_token()

    tracking = _db_tracking_available() if use_db_lock else None
    conn = None
    run_row_id = None
    try:
        if tracking:
            engine, text, PipelineRun = tracking
            conn = engine.connect()
            locked = bool(conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": PIPELINE_LOCK_KEY}).scalar())
            if not locked:
                print("pipeline skipped: another run holds the advisory lock", file=sys.stderr)
                return 75
            with engine.begin() as tx:
                from sqlalchemy import update
                # A previous process may have died while holding the session lock.
                # Once we own the lock, any remaining `running` row is stale.
                tx.execute(
                    update(PipelineRun)
                    .where(PipelineRun.status == "running")
                    .values(status="abandoned", finished_at=started, error_code="PROCESS_RESTART")
                )
                row = PipelineRun(run_id=run_id, status="running", started_at=started, current_stage="starting")
                from sqlalchemy.orm import Session
                with Session(bind=tx) as session:
                    session.add(row)
                    session.flush()
                    run_row_id = row.id

        for index, stage in enumerate(list(stages or default_stages()), start=1):
            print(f"[{index}] {stage.name} ...")
            if tracking and run_row_id:
                engine, _, PipelineRun = tracking
                from sqlalchemy import update
                with engine.begin() as tx:
                    tx.execute(update(PipelineRun).where(PipelineRun.id == run_row_id).values(current_stage=stage.name))
            stage.runner()

        finished = datetime.now(timezone.utc)
        if tracking and run_row_id:
            engine, _, PipelineRun = tracking
            from sqlalchemy import update
            with engine.begin() as tx:
                tx.execute(update(PipelineRun).where(PipelineRun.id == run_row_id).values(status="success", current_stage="complete", finished_at=finished))
        print(f"pipeline run_id={run_id} success finished_at={finished.isoformat()}")
        return 0
    except Exception as exc:
        finished = datetime.now(timezone.utc)
        print(f"pipeline run_id={run_id} failed type={type(exc).__name__}", file=sys.stderr)
        if tracking and run_row_id:
            try:
                engine, _, PipelineRun = tracking
                from sqlalchemy import update
                with engine.begin() as tx:
                    tx.execute(update(PipelineRun).where(PipelineRun.id == run_row_id).values(status="failed", finished_at=finished, error_code=type(exc).__name__))
            except Exception:
                pass
        exit_code = getattr(exc, "exit_code", 1)
        return exit_code if isinstance(exit_code, int) and 0 < exit_code < 256 else 1
    finally:
        if conn is not None:
            try:
                from sqlalchemy import text
                conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": PIPELINE_LOCK_KEY})
            finally:
                conn.close()


def main() -> None:
    raise SystemExit(run_pipeline())


if __name__ == "__main__":
    main()
