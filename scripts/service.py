#!/usr/bin/env python3
"""Cross-platform service manager for Graphics Engine Radar (API + Web).

    uv run python scripts/service.py start    # start API (:8300) and Web (:8301) in background
    uv run python scripts/service.py stop     # stop both (and their child processes)
    uv run python scripts/service.py status   # show state
    uv run python scripts/service.py restart

Works on Windows / macOS / Linux. PID files live in <repo>/data/services/.
Database is managed separately: scripts/embedded_db.py (start|stop|status).
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PID_DIR = ROOT / "data" / "services"
LOG_DIR = ROOT / "data" / "logs"

SERVICES = {
    "api": {
        "port": 8300,
        "cwd": ROOT,
        "cmd": ["uv", "run", "uvicorn", "radar_api.app:app", "--port", "8300"],
    },
    "web": {
        "port": 8301,
        "cwd": ROOT / "apps" / "web",
        "cmd": ["npm", "run", "dev"],
    },
}


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _pid_file(name: str) -> Path:
    return PID_DIR / f"{name}.pid"


def _proc_alive(pid: int) -> bool:
    try:
        import psutil

        return psutil.pid_exists(pid)
    except ImportError:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _spawn(name: str) -> None:
    svc = SERVICES[name]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    cmd = list(svc["cmd"])
    # resolve npm/npm.cmd and uv without shell
    resolved = subprocess.run(["where" if os.name == "nt" else "which", cmd[0]],
                              capture_output=True, text=True)
    if resolved.returncode == 0:
        cmd[0] = resolved.stdout.strip().splitlines()[0]
    log = open(LOG_DIR / f"{name}.log", "ab")
    kwargs: dict = {"cwd": str(svc["cwd"]), "stdout": log, "stderr": log,
                    "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    _pid_file(name).write_text(str(proc.pid))
    print(f"[{name}] started pid={proc.pid} port={svc['port']}")


def start(name: str) -> None:
    if _port_open(SERVICES[name]["port"]):
        print(f"[{name}] already running on :{SERVICES[name]['port']}")
        return
    pidf = _pid_file(name)
    if pidf.exists() and _proc_alive(int(pidf.read_text())):
        print(f"[{name}] process {pidf.read_text()} alive but port closed; restarting")
        stop(name)
    _spawn(name)


def stop(name: str) -> None:
    pidf = _pid_file(name)
    pid = int(pidf.read_text()) if pidf.exists() else None
    try:
        import psutil

        if pid and psutil.pid_exists(pid):
            parent = psutil.Process(pid)
            procs = [parent, *parent.children(recursive=True)]
            for p in procs:
                p.terminate()
            _, alive = psutil.wait_procs(procs, timeout=8)
            for p in alive:
                p.kill()
            print(f"[{name}] stopped (pid {pid})")
        else:
            print(f"[{name}] not running (no pid record)")
    except ImportError:
        if pid:
            os.kill(pid, 15)
            print(f"[{name}] sent SIGTERM to {pid}")
        else:
            print(f"[{name}] not running")
    except psutil.NoSuchProcess:
        print(f"[{name}] already gone")
    finally:
        pidf.unlink(missing_ok=True)


def status() -> None:
    for name, svc in SERVICES.items():
        up = _port_open(svc["port"])
        pidf = _pid_file(name)
        pid = pidf.read_text() if pidf.exists() else "-"
        print(f"{name:4s} :{svc['port']}  {'RUNNING' if up else 'stopped'}  (pid {pid})")
    # database hint
    pgdata = Path(os.environ.get("GRADAR_DATA_DIR", ROOT / "data" / "pgdata"))
    pidfile = pgdata / "postmaster.pid"
    if pidfile.exists():
        print("db   : embedded postgres pid file present (scripts/embedded_db.py status for detail)")
    else:
        print("db   : no embedded postgres pid file (external DB if configured in .env)")


def wait_ready(timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    for name, svc in SERVICES.items():
        while time.time() < deadline and not _port_open(svc["port"]):
            time.sleep(0.5)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "start":
        for name in SERVICES:
            start(name)
        wait_ready()
        status()
    elif cmd == "stop":
        for name in SERVICES:
            stop(name)
    elif cmd == "restart":
        for name in SERVICES:
            stop(name)
        for name in SERVICES:
            start(name)
        wait_ready()
        status()
    elif cmd == "status":
        status()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
