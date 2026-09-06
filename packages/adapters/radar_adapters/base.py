from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from radar_domain.models import Source


@dataclass
class RawItemDraft:
    """Normalized output of one adapter fetch, before DB persistence."""

    external_id: str
    url: str | None = None
    canonical_url: str | None = None
    title: str = ""
    content: str = ""
    author: str | None = None
    published_at: datetime | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchResult:
    items: list[RawItemDraft]
    next_cursor: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(ABC):
    """Adapter interface (spec §19/§6): fetch(cursor) -> FetchResult.

    Implementations must be idempotent and cursor-based: given the same
    cursor, fetching again must not produce duplicates.
    """

    name: str = "base"

    @abstractmethod
    async def fetch(self, source: Source, cursor: str | None) -> FetchResult:
        ...


_REGISTRY: dict[str, type[SourceAdapter]] = {}


def register(cls: type[SourceAdapter]) -> type[SourceAdapter]:
    _REGISTRY[cls.name] = cls
    return cls


def get_adapter(name: str) -> SourceAdapter:
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        raise KeyError(f"unknown adapter: {name!r}; known: {sorted(_REGISTRY)}") from exc


def known_adapters() -> list[str]:
    return sorted(_REGISTRY)
