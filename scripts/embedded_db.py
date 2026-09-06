#!/usr/bin/env python3
"""Embedded database mode — the simplest cross-platform deployment (Windows /
macOS / Linux, no Docker, no WSL, no manual Postgres install).

Uses the `pgserver` pip package, which bundles PostgreSQL + pgvector binaries:
    uv run python scripts/embedded_db.py start    # init+start, create db, alembic, .env
    uv run python scripts/embedded_db.py status
    uv run python scripts/embedded_db.py uri
    uv run python scripts/embedded_db.py stop

Data directory: <repo>/data/pgdata (override with GRADAR_DATA_DIR).
After `start`, the normal commands work unchanged:
    uv run radar-collector sync-config
    uv run python scripts/pipeline.py
    uv run uvicorn radar_api.app:app --port 8300
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PGDATA = Path(os.environ.get("GRADAR_DATA_DIR", ROOT / "data" / "pgdata"))
DB_NAME = "radar"
ENV_FILE = ROOT / ".env"


def _server(cleanup_mode: str | None = None):
    import pgserver

    PGDATA.parent.mkdir(parents=True, exist_ok=True)
    return pgserver.get_server(str(PGDATA), cleanup_mode=cleanup_mode)


def _write_env(database_url: str) -> None:
    """Create or update DATABASE_URL in .env without touching other keys."""
    lines: list[str] = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    replaced = False
    out = []
    for line in lines:
        if line.strip().startswith("DATABASE_URL="):
            out.append(f"DATABASE_URL={database_url}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.insert(0, f"DATABASE_URL={database_url}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.environ["DATABASE_URL"] = database_url


def _sqlalchemy_url(pg_uri: str) -> str:
    # postgresql://... -> postgresql+psycopg://... (psycopg3 driver)
    if pg_uri.startswith("postgresql://"):
        return "postgresql+psycopg://" + pg_uri[len("postgresql://"):]
    return pg_uri


def _running_pid() -> int | None:
    """Passively check for a running postgres on PGDATA (must NOT call
    get_server: it auto-starts the server as a side effect)."""
    pidfile = PGDATA / "postmaster.pid"
    if not pidfile.exists():
        return None
    try:
        pid = int(pidfile.read_text().splitlines()[0])
    except (ValueError, OSError):
        return None
    import psutil

    try:
        proc = psutil.Process(pid)
        if "postgres" not in proc.name().lower():
            return None
        return pid
    except psutil.NoSuchProcess:
        return None


def cmd_start() -> None:
    print(f"[embedded-pg] data dir: {PGDATA}")
    server = _server(cleanup_mode=None)  # keep running after this script exits
    uri = server.get_uri(DB_NAME)
    import psycopg

    with psycopg.connect(server.get_uri("postgres"), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"[embedded-pg] created database {DB_NAME}")

    with psycopg.connect(uri, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    print(f"[embedded-pg] running: {uri}")

    sa_url = _sqlalchemy_url(uri)
    _write_env(sa_url)
    print(f"[embedded-pg] DATABASE_URL written to {ENV_FILE.name}")

    # apply migrations in-process (imports read the updated DATABASE_URL)
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(cfg, "head")
    print("[embedded-pg] migrations applied (alembic upgrade head)")
    print("[embedded-pg] ready. next: uv run radar-collector sync-config")


def cmd_status() -> None:
    print("running" if _running_pid() else "stopped")


def cmd_uri() -> None:
    if not _running_pid():
        print("stopped (run: uv run python scripts/embedded_db.py start)")
        sys.exit(1)
    server = _server(cleanup_mode=None)
    print(_sqlalchemy_url(server.get_uri(DB_NAME)))


def cmd_stop() -> None:
    if not _running_pid():
        print("[embedded-pg] not running")
        return
    try:
        from pgserver import pg_ctl

        out = pg_ctl(["stop", "-m", "fast"], pgdata=PGDATA)
        print("[embedded-pg] stopped:", out.strip().splitlines()[-1]
              if out.strip() else "ok")
    except Exception as exc:
        print(f"[embedded-pg] stop failed: {exc}")
        sys.exit(1)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    {"start": cmd_start, "stop": cmd_stop, "status": cmd_status, "uri": cmd_uri}[cmd]()


if __name__ == "__main__":
    main()
