#!/usr/bin/env python3
"""Cross-platform pipeline runner: collect -> intelligence -> trends -> digests.

Works on macOS / Linux / Windows (PowerShell or cmd):
    uv run python scripts/pipeline.py
Idempotent: repeated runs only process increments.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radar_collector.cli import collector  # noqa: E402
from radar_intelligence.cli import intelligence  # noqa: E402


def main() -> None:
    if not os.environ.get("GITHUB_TOKEN"):
        try:
            import subprocess

            token = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True, check=True
            ).stdout.strip()
            if token:
                os.environ["GITHUB_TOKEN"] = token
                print("[github] using gh auth token")
        except Exception:
            print("[github] no GITHUB_TOKEN / gh CLI - limited to 60 req/h")

    print("[1/4] collecting sources ...")
    collector(["run-all"])

    print("[2/4] intelligence pipeline ...")
    intelligence(["process"])

    print("[3/4] trend snapshots ...")
    intelligence(["trends"])

    print("[4/4] digests ...")
    for kind in ("daily", "weekly", "monthly"):
        intelligence(["digest", "--kind", kind])

    print("\ndone. open http://localhost:8301")


if __name__ == "__main__":
    main()
