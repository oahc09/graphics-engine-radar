"""Public error handling with request correlation and conservative redaction."""
from __future__ import annotations

import logging
import re
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("radar_api.errors")

_SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization|api[-_]?key|token|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)\b(?:postgres(?:ql)?|https?)://[^\s]+"),
]


def _safe_error_text(exc: Exception) -> str:
    text = str(exc).replace("\r", " ").replace("\n", " ")[:500]
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    request.state.request_id = request_id[:128]
    response = await call_next(request)
    response.headers["x-request-id"] = request.state.request_id
    return response


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    # Do not emit a traceback/absolute paths or raw exception text. The request
    # id + exception class + redacted message is enough to correlate controlled
    # server logs without reflecting internals to the caller.
    log.error(
        "request failed request_id=%s method=%s path=%s type=%s detail=%s",
        request_id,
        request.method,
        request.url.path,
        type(exc).__name__,
        _safe_error_text(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "request failed", "request_id": request_id},
        headers={"x-request-id": request_id},
    )
