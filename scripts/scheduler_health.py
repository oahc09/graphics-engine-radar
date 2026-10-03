#!/usr/bin/env python3
"""Scheduler health probe: process health plus durable scheduling freshness."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone


def main() -> int:
    interval = int(os.getenv("PIPELINE_INTERVAL_SECONDS", "3600"))
    timeout = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "3600"))
    grace = int(os.getenv("SCHEDULER_HEALTH_GRACE_SECONDS", "600"))
    max_age = timedelta(seconds=interval + timeout + grace)
    try:
        from radar_domain.db import session_scope
        from radar_domain.pipeline_state import SchedulerState
        with session_scope() as session:
            state = session.get(SchedulerState, "pipeline")
            if state is None or state.updated_at is None:
                return 1
            updated = state.updated_at
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - updated > max_age:
                return 1
            return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
