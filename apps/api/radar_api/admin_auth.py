"""Fail-closed authentication for the optional admin API."""
from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


def admin_enabled() -> bool:
    return os.getenv("ENABLE_ADMIN_API", "false").strip().lower() in {"1", "true", "yes", "on"}


def require_admin(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("ADMIN_API_TOKEN", "")
    if not admin_enabled() or not expected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
