from __future__ import annotations

from datetime import datetime, timezone

import feedparser
import httpx
from bs4 import BeautifulSoup

from radar_adapters.base import FetchResult, RawItemDraft, SourceAdapter, register
from radar_adapters.normalize import canonical_url
from radar_domain.settings import get_settings


def _clean_html(html: str, limit: int = 20000) -> str:
    soup = BeautifulSoup(html or "", "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)[:limit]


@register
class RSSAdapter(SourceAdapter):
    """Fetch RSS/Atom feeds (covers rss, official_blog, community types)."""

    name = "rss"

    async def fetch(self, source: Source, cursor: str | None) -> FetchResult:
        url = source.url or (source.config or {}).get("url")
        if not url:
            raise ValueError(f"rss source {source.id} has no url")
        limit = get_settings().collector_max_items_per_fetch
        async with httpx.AsyncClient(timeout=get_settings().http_timeout_seconds,
                                     follow_redirects=True,
                                     headers={"User-Agent": "graphics-engine-radar/0.1"}) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        parsed = feedparser.parse(resp.content)

        items: list[RawItemDraft] = []
        newest = cursor
        for entry in parsed.entries[:limit]:
            link = entry.get("link")
            stamp = None
            for key in ("published", "updated"):
                raw = entry.get(f"{key}_parsed")
                if raw:
                    stamp = datetime(*raw[:6], tzinfo=timezone.utc)
                    break
            stamp_iso = stamp.isoformat() if stamp else None
            if cursor and stamp_iso and stamp_iso <= cursor:
                continue
            summary = entry.get("summary") or ""
            content_field = ""
            if entry.get("content"):
                content_field = entry["content"][0].get("value", "")
            body = _clean_html(content_field or summary)
            items.append(RawItemDraft(
                external_id=entry.get("id") or link or (entry.get("title", "")[:200]),
                url=link,
                canonical_url=canonical_url(link),
                title=entry.get("title", "").strip(),
                content=f"{entry.get('title', '')}\n\n{body}".strip(),
                author=entry.get("author"),
                published_at=stamp,
                raw_payload={"feed": url, "entry_id": entry.get("id")},
            ))
            if stamp_iso and (newest is None or stamp_iso > newest):
                newest = stamp_iso
        return FetchResult(items=items, next_cursor=newest,
                           metadata={"feed": url, "count": len(items)})


@register
class HTMLAdapter(SourceAdapter):
    """Fetch a page and extract readable text. Produces a single RawItem whose
    content_hash changes when the page changes (for release-notes style pages)."""

    name = "html"

    async def fetch(self, source: Source, cursor: str | None) -> FetchResult:
        url = source.url or (source.config or {}).get("url")
        if not url:
            raise ValueError(f"html source {source.id} has no url")
        async with httpx.AsyncClient(timeout=get_settings().http_timeout_seconds,
                                     follow_redirects=True,
                                     headers={"User-Agent": "graphics-engine-radar/0.1"}) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        text = _clean_html(resp.text)
        canon = canonical_url(url)
        content = text[:20000]
        from radar_adapters.normalize import content_hash
        h = content_hash(content)
        items: list[RawItemDraft] = []
        if cursor and h == cursor:
            return FetchResult(items=[], next_cursor=cursor,
                               metadata={"url": url, "unchanged": True})
        items.append(RawItemDraft(
            external_id=canon or url,
            url=url,
            canonical_url=canon,
            title=(source.config or {}).get("title") or (url.rstrip("/").split("/")[-1] or url),
            content=content,
            published_at=datetime.now(timezone.utc) if cursor else None,
            raw_payload={"page": url, "text_length": len(text)},
        ))
        return FetchResult(items=items, next_cursor=h,
                           metadata={"url": url, "count": len(items)})


@register
class ReleaseNotesAdapter(HTMLAdapter):
    """Alias of HTMLAdapter with release-notes semantics: the page content is
    the release notes document; a change of content hash is a new RawItem."""

    name = "release_notes"


@register
class SpecRegistryAdapter(HTMLAdapter):
    """Watch a specification/registry page (spec §5/§19). Same page-hash
    semantics as HTMLAdapter; spec changes are rare and high-value."""

    name = "spec_registry"
