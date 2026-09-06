"""LLM access + AI traceability (spec §36).

Three provider backends, selected by LLM_PROVIDER:
- openai     OpenAI-compatible chat/completions over HTTP (OpenAI, DeepSeek,
             Qwen, GLM/Z.ai, Moonshot, OpenRouter, Ollama, LM Studio, ...,
             including Claude via OpenRouter or Anthropic's compat endpoint).
             Requires LLM_API_KEY.
- claude-cli shells out to the local `claude` CLI (Claude Code print mode).
             Uses the logged-in Claude subscription; no API key.
- codex-cli  shells out to the local `codex` CLI (codex exec).
             Uses the logged-in ChatGPT account; no API key.

Every call is recorded in AIExecution with model, prompt_version, input_hash,
input/output payloads and failure info. LLM_STAGES gates which pipeline stages
may call the LLM (empty = all); skipped stages fall back to heuristics and are
recorded as such.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from radar_domain.db import session_scope
from radar_domain.models import AIExecution
from radar_domain.settings import get_settings

log = logging.getLogger("intelligence.llm")


def input_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of arbitrary model output: handles ```json fences,
    prose around the object, and trailing log lines (codex exec prints extra
    output after the final message).

    Strategy: collect every balanced {...} span plus any fenced blocks, then
    take the longest parseable dict (the outer object beats its own nested
    ones; among separate objects, longer/later wins)."""
    if not text:
        raise json.JSONDecodeError("empty output", "", 0)
    spans: list[str] = [c.strip() for c in
                        re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)]
    body = text.strip()
    objects: list[tuple[int, str]] = []
    for m in re.finditer(r"\{", body):
        start = m.start()
        depth = 0
        end = None
        for i in range(start, len(body)):
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is not None:
            objects.append((start, body[start:end]))
    # longest parseable span wins; ties -> the later one (final answer at end)
    objects.sort(key=lambda t: (len(t[1]), t[0]))
    candidates = [text for _, text in reversed(objects)] + spans + [body]
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            return obj
    raise json.JSONDecodeError("no JSON object found in output", text[:120], 0)


def record_ai_execution(
    stage: str,
    model: str,
    prompt_version: str,
    input_hash: str,
    input_payload: dict,
    output_payload: dict,
    success: bool,
    error: str | None = None,
) -> None:
    try:
        with session_scope() as session:
            session.add(AIExecution(
                pipeline_stage=stage,
                model=model,
                prompt_version=prompt_version,
                input_hash=input_hash,
                input_payload=input_payload,
                output_payload=output_payload,
                success=success,
                error=error,
            ))
    except Exception:  # tracing must never break the pipeline
        log.exception("failed to record AIExecution")


def stage_enabled(stage: str) -> bool:
    allowed = get_settings().llm_stages.strip()
    if not allowed:
        return True
    return stage in {s.strip() for s in allowed.split(",") if s.strip()}


class LLMClient:
    """Provider-dispatching chat client with JSON-mode helpers."""

    def __init__(self) -> None:
        settings = get_settings()
        self.provider = settings.llm_provider.strip().lower()
        self.api_base = settings.llm_api_base.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model.strip()
        self.timeout = settings.llm_cli_timeout

    @property
    def model_label(self) -> str:
        if self.provider == "claude-cli":
            return f"claude-cli:{self.model or 'default'}"
        if self.provider == "codex-cli":
            return f"codex-cli:{self.model or 'default'}"
        return self.model or "gpt-4o-mini"

    @property
    def enabled(self) -> bool:
        if self.provider == "claude-cli":
            return shutil.which("claude") is not None
        if self.provider == "codex-cli":
            return shutil.which("codex") is not None
        return bool(self.api_key)

    # ------------------------------------------------------------------ CLI
    def _cli_chat_json(self, system: str, user: str) -> dict[str, Any]:
        prompt = f"{system}\n\n---\n\n{user}"
        if self.provider == "claude-cli":
            cmd = ["claude", "-p", prompt]
            if self.model:
                cmd += ["--model", self.model]
        else:  # codex-cli
            cmd = ["codex", "exec", "--skip-git-repo-check"]
            if self.model:
                cmd += ["-m", self.model]
            cmd.append(prompt)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout,
            cwd=str(Path(__file__).resolve().parents[4]),
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"{self.provider} exited {proc.returncode}: {proc.stderr.strip()[:300]}")
        return extract_json(proc.stdout)

    # ----------------------------------------------------------------- HTTP
    def _http_chat_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("LLM not configured (LLM_API_KEY empty)")
        model = self.model or "gpt-4o-mini"
        with httpx.Client(timeout=max(self.timeout, 90.0)) as client:
            resp = client.post(
                f"{self.api_base}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return extract_json(text)

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        if self.provider == "claude-cli":
            return self._cli_chat_json(system, user)
        if self.provider == "codex-cli":
            return self._cli_chat_json(system, user)
        return self._http_chat_json(system, user)


def parse_structured(model_cls: type[BaseModel], data: dict) -> BaseModel:
    """Strict schema validation: invalid JSON/schema never advances stages."""
    return model_cls.model_validate(data)


def run_fallback(stage: str, prompt_version: str, input_payload: dict,
                 output_payload: dict) -> dict:
    """Record a heuristic (non-LLM) stage decision for traceability."""
    ih = input_hash(input_payload)
    record_ai_execution(stage, model="heuristic-rules", prompt_version=prompt_version,
                        input_hash=ih, input_payload=input_payload,
                        output_payload=output_payload, success=True)
    return output_payload


async def run_llm_stage(stage: str, prompt_version: str, input_payload: dict,
                        system: str, user: str, model_cls: type[BaseModel]) -> tuple[dict | None, str]:
    """Execute an LLM stage; returns (validated_output_dict, model_used).
    On any failure records the error and returns (None, model)."""
    if not stage_enabled(stage):
        record_ai_execution(stage, model="heuristic-rules", prompt_version=prompt_version,
                            input_hash=input_hash(input_payload),
                            input_payload=input_payload,
                            output_payload={"skipped": "stage_not_in_llm_stages"},
                            success=True)
        return None, "heuristic-rules"

    client = LLMClient()
    ih = input_hash(input_payload)
    if not client.enabled:
        record_ai_execution(stage, model="heuristic-rules", prompt_version=prompt_version,
                            input_hash=ih, input_payload=input_payload,
                            output_payload={"skipped": "llm_not_configured"}, success=True)
        return None, "heuristic-rules"
    try:
        raw = client.chat_json(system, user)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, OSError,
            subprocess.TimeoutExpired, RuntimeError) as exc:
        record_ai_execution(stage, model=client.model_label, prompt_version=prompt_version,
                            input_hash=ih, input_payload=input_payload,
                            output_payload={}, success=False,
                            error=f"{type(exc).__name__}: {exc}")
        return None, client.model_label
    try:
        validated = parse_structured(model_cls, raw)
    except ValidationError as exc:
        record_ai_execution(stage, model=client.model_label, prompt_version=prompt_version,
                            input_hash=ih, input_payload=input_payload,
                            output_payload=raw, success=False,
                            error=f"schema validation failed: {exc}")
        return None, client.model_label
    out = validated.model_dump()
    record_ai_execution(stage, model=client.model_label, prompt_version=prompt_version,
                        input_hash=ih, input_payload=input_payload,
                        output_payload=out, success=True)
    return out, client.model_label
