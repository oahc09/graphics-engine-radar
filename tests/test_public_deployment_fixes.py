from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import click
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_admin_guard_denies_missing_and_bad_credentials(monkeypatch):
    mod = load_module("radar_admin_auth", ROOT / "apps/api/radar_api/admin_auth.py")
    app = FastAPI()
    from fastapi import Depends

    @app.post("/admin/probe", dependencies=[Depends(mod.require_admin)])
    def probe():
        return {"ok": True}

    monkeypatch.setenv("ENABLE_ADMIN_API", "true")
    monkeypatch.setenv("ADMIN_API_TOKEN", "unit-test-secret")
    client = TestClient(app)
    assert client.post("/admin/probe").status_code == 401
    assert client.post("/admin/probe", headers={"authorization": "Bearer wrong"}).status_code == 401
    assert client.post("/admin/probe", headers={"x-forwarded-user": "admin"}).status_code == 401
    assert client.post("/admin/probe", headers={"authorization": "Bearer unit-test-secret"}).status_code == 200


def test_admin_guard_fail_closed_when_disabled(monkeypatch):
    mod = load_module("radar_admin_auth_disabled", ROOT / "apps/api/radar_api/admin_auth.py")
    monkeypatch.setenv("ENABLE_ADMIN_API", "false")
    monkeypatch.setenv("ADMIN_API_TOKEN", "unit-test-secret")
    with pytest.raises(Exception) as exc:
        mod.require_admin("Bearer unit-test-secret")
    assert getattr(exc.value, "status_code", None) == 404

def test_public_object_response_does_not_expose_last_error():
    source = (ROOT / "apps/api/radar_api/app.py").read_text()
    object_handler = source.split('def get_object',1)[1].split('@app.get("/topics")',1)[0]
    assert '"last_error"' not in object_handler


def test_internal_errors_are_sanitized():
    mod = load_module("radar_security", ROOT / "apps/api/radar_api/security.py")
    app = FastAPI()
    app.middleware("http")(mod.request_id_middleware)
    app.add_exception_handler(Exception, mod.unhandled_exception_handler)

    @app.get("/boom")
    def boom():
        raise RuntimeError("SECRET_MARKER db=postgresql://u:p@internal:5432/radar")

    client = TestClient(app, raise_server_exceptions=False)
    res = client.get("/boom")
    assert res.status_code == 500
    body = res.text
    assert "SECRET_MARKER" not in body and "postgresql://" not in body and "internal:5432" not in body
    assert res.json()["error"] == "internal_error"
    assert res.json()["request_id"] == res.headers["x-request-id"]


def test_next_config_builds_without_runtime_api_target():
    env = dict(os.environ, NODE_ENV="production")
    env.pop("INTERNAL_API_BASE", None)
    env.pop("API_PROXY_TARGET", None)
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", "import('./apps/web/next.config.mjs')"],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_runtime_proxy_is_explicit_public_allowlist_and_no_admin():
    source = (ROOT / "apps/web/app/api/[...path]/route.ts").read_text()
    assert "PUBLIC_ROUTES" in source
    assert "API_PROXY_TARGET || process.env.INTERNAL_API_BASE" in source
    assert "service_unavailable" in source
    assert "admin" not in source.lower()
    for route in ("health", "events", "selected", "objects", "topics", "trends", "digests", "metrics"):
        assert route in source


def test_runtime_proxy_is_get_only_and_has_no_open_proxy_target():
    source = (ROOT / "apps/web/app/api/[...path]/route.ts").read_text()
    assert "export const GET" in source
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        assert f"export const {method}" not in source
    assert "new URL(`${base}/${path}`)" in source
    assert "request.nextUrl.search" in source


def test_ssr_client_has_no_loopback_fallback():
    source = (ROOT / "apps/web/lib/api.ts").read_text()
    assert "127.0.0.1:8300" not in source
    assert "INTERNAL_API_BASE" in source
    assert 'NEXT_PUBLIC_API_BASE || "/api"' in source


def test_pipeline_runs_all_stages_in_order():
    mod = load_module("pipeline_script", ROOT / "scripts/pipeline.py")
    seen=[]
    stages=[mod.Stage("one",lambda:seen.append("one")),mod.Stage("two",lambda:seen.append("two")),mod.Stage("three",lambda:seen.append("three"))]
    assert mod.run_pipeline(stages,use_db_lock=False)==0
    assert seen==["one","two","three"]


def test_pipeline_failure_stops_dependents_and_returns_nonzero():
    mod = load_module("pipeline_script_fail", ROOT / "scripts/pipeline.py")
    seen=[]
    def fail():
        seen.append("fail"); raise RuntimeError("controlled failure")
    stages=[mod.Stage("one",lambda:seen.append("one")),mod.Stage("fail",fail),mod.Stage("never",lambda:seen.append("never"))]
    assert mod.run_pipeline(stages,use_db_lock=False)==1
    assert seen==["one","fail"]


def test_click_nonstandalone_does_not_exit_on_success_and_propagates_failure():
    mod = load_module("pipeline_click", ROOT / "scripts/pipeline.py")
    @click.group()
    def cli(): pass
    @cli.command("ok")
    def ok(): return None
    @cli.command("bad")
    def bad(): raise click.ClickException("boom")
    mod._invoke_click(cli,["ok"])
    with pytest.raises(click.ClickException): mod._invoke_click(cli,["bad"])


def test_scheduler_has_bounded_retry_restart_loop_and_calls_single_entrypoint():
    source=(ROOT/"scripts/scheduler.py").read_text()
    assert 'scripts" / "pipeline.py"' in source
    assert "PIPELINE_MAX_RETRIES" in source
    assert "PIPELINE_TIMEOUT_SECONDS" in source
    assert "while True" in source


def test_compose_scheduler_and_network_exposure():
    text=(ROOT/"docker-compose.yml").read_text()
    assert "scheduler:" in text and "scripts/scheduler.py" in text
    # API and database have no host ports; only web has a published binding.
    postgres=text.split("  postgres:",1)[1].split("  migrate:",1)[0]
    api=text.split("  api:",1)[1].split("  scheduler:",1)[0]
    assert "ports:" not in postgres and "ports:" not in api
    assert "WEB_BIND_ADDRESS:-127.0.0.1" in text
    assert "service_completed_successfully" in text


def test_pipeline_lock_contention_skips_without_running(monkeypatch):
    mod = load_module("pipeline_lock_contention", ROOT / "scripts/pipeline.py")
    seen = []

    class Result:
        def scalar(self):
            return False

    class Conn:
        def execute(self, *args, **kwargs):
            return Result()
        def close(self):
            pass

    class Engine:
        def connect(self):
            return Conn()

    monkeypatch.setattr(mod, "_db_tracking_available", lambda: (Engine(), lambda x: x, object))
    code = mod.run_pipeline([mod.Stage("must_not_run", lambda: seen.append("ran"))])
    assert code == 75
    assert seen == []


def test_scheduler_failure_retry_is_bounded(monkeypatch):
    mod = load_module("scheduler_retry", ROOT / "scripts/scheduler.py")
    calls = []
    sequence = iter([1, 1, 0])
    monkeypatch.setattr(mod, "run_once", lambda: calls.append("run") or next(sequence))
    monkeypatch.setattr(mod, "_record_state", lambda **kwargs: None)
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    assert mod.execute_with_retries(max_retries=2, retry_delay=10) == 0
    assert len(calls) == 3


def test_scheduler_restart_model_has_no_in_memory_lock(monkeypatch):
    mod1 = load_module("scheduler_restart_one", ROOT / "scripts/scheduler.py")
    mod2 = load_module("scheduler_restart_two", ROOT / "scripts/scheduler.py")
    # Fresh scheduler processes share only the DB-backed pipeline lock/status;
    # there is no process-local boolean that can remain stuck after restart.
    source = (ROOT / "scripts/scheduler.py").read_text()
    assert "pg_try_advisory_lock" not in source
    assert "scripts" in str(mod1.PIPELINE) and mod1.PIPELINE == mod2.PIPELINE
    assert "SchedulerState" in source


def test_api_image_contains_scheduler_entrypoint():
    text = (ROOT / "docker/api.Dockerfile").read_text()
    assert "COPY scripts ./scripts" in text


def test_error_log_redacts_connection_and_secret_marker(caplog):
    mod = load_module("radar_security_log", ROOT / "apps/api/radar_api/security.py")
    safe = mod._safe_error_text(RuntimeError("Authorization=Bearer-secret postgresql://u:p@internal:5432/radar"))
    assert "Bearer-secret" not in safe
    assert "postgresql://" not in safe
    assert "internal:5432" not in safe


def test_click_explicit_exit_is_failure_not_systemexit_success():
    mod = load_module("pipeline_click_exit", ROOT / "scripts/pipeline.py")

    @click.group()
    def cli():
        pass

    @cli.command("exit-seven")
    @click.pass_context
    def exit_seven(ctx):
        ctx.exit(7)

    with pytest.raises(click.exceptions.Exit) as exc:
        mod._invoke_click(cli, ["exit-seven"])
    assert exc.value.exit_code == 7
    stage = mod.Stage("exit-seven", lambda: mod._invoke_click(cli, ["exit-seven"]))
    assert mod.run_pipeline([stage], use_db_lock=False) == 7


def test_restart_recovery_marks_stale_run_abandoned():
    source = (ROOT / "scripts/pipeline.py").read_text()
    assert 'status="abandoned"' in source
    assert 'error_code="PROCESS_RESTART"' in source


def test_compose_has_all_four_service_health_boundaries():
    text = (ROOT / "docker-compose.yml").read_text()
    assert text.count("healthcheck:") >= 5  # postgres, redis, api, scheduler, web
    assert "scheduler_health.py" in text
    assert "/health" in text
