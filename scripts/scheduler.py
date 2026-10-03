#!/usr/bin/env python3
"""Persistent scheduler for the single pipeline entrypoint.

Only this process owns cadence/retry policy. Every actual run goes through
scripts/pipeline.py, whose PostgreSQL advisory lock prevents overlap across
manual/scheduled processes and across hosts that share the database.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "scripts" / "pipeline.py"


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def run_once() -> int:
    timeout = _int_env("PIPELINE_TIMEOUT_SECONDS", 3600, 60)
    proc = subprocess.run([sys.executable, str(PIPELINE)], cwd=ROOT, timeout=timeout)
    return proc.returncode


def _record_state(*, next_run_at=None, success_at=None, failure_at=None, exit_code=None) -> None:
    """Best-effort durable status. A status-write failure never invents success."""
    try:
        from sqlalchemy.dialects.postgresql import insert
        from radar_domain.db import engine
        from radar_domain.pipeline_state import SchedulerState

        values = {"name": "pipeline", "updated_at": datetime.now(timezone.utc)}
        if next_run_at is not None:
            values["next_run_at"] = next_run_at
        if success_at is not None:
            values["last_success_at"] = success_at
        if failure_at is not None:
            values["last_failure_at"] = failure_at
        if exit_code is not None:
            values["last_exit_code"] = exit_code
        stmt = insert(SchedulerState).values(**values)
        update_values = {k: v for k, v in values.items() if k != "name"}
        stmt = stmt.on_conflict_do_update(index_elements=[SchedulerState.name], set_=update_values)
        with engine.begin() as conn:
            conn.execute(stmt)
    except Exception as exc:
        print(f"scheduler state persistence unavailable: {type(exc).__name__}", file=sys.stderr, flush=True)


def execute_with_retries(max_retries: int, retry_delay: int) -> int:
    """Run once plus bounded retries. Exit 75 means lock contention, not failure."""
    attempt = 0
    while True:
        attempt += 1
        try:
            code = run_once()
        except subprocess.TimeoutExpired:
            code = 124
            print("pipeline timed out", file=sys.stderr, flush=True)
        now = datetime.now(timezone.utc)
        if code == 0:
            _record_state(success_at=now, exit_code=code)
            return code
        if code == 75:
            return code
        _record_state(failure_at=now, exit_code=code)
        if attempt > max_retries:
            print(f"pipeline failed code={code}; retries exhausted", file=sys.stderr, flush=True)
            return code
        print(f"pipeline failed code={code}; retrying in {retry_delay}s", file=sys.stderr, flush=True)
        time.sleep(retry_delay)


def main() -> None:
    interval = _int_env("PIPELINE_INTERVAL_SECONDS", 3600, 60)
    retry_delay = _int_env("PIPELINE_RETRY_DELAY_SECONDS", 300, 10)
    max_retries = _int_env("PIPELINE_MAX_RETRIES", 1, 0)
    run_on_start = os.getenv("PIPELINE_RUN_ON_START", "true").lower() in {"1", "true", "yes", "on"}
    now = datetime.now(timezone.utc)
    next_run = now if run_on_start else now + timedelta(seconds=interval)
    _record_state(next_run_at=next_run)
    print(f"scheduler started interval={interval}s next_run={next_run.isoformat()}", flush=True)
    while True:
        now = datetime.now(timezone.utc)
        if now < next_run:
            time.sleep(min(30, max(1, int((next_run - now).total_seconds()))))
            continue
        execute_with_retries(max_retries=max_retries, retry_delay=retry_delay)
        next_run = datetime.now(timezone.utc) + timedelta(seconds=interval)
        _record_state(next_run_at=next_run)
        print(f"next_run={next_run.isoformat()}", flush=True)


if __name__ == "__main__":
    main()
