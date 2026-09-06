from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from radar_adapters.base import FetchResult, RawItemDraft, SourceAdapter, register
from radar_adapters.normalize import canonical_url
from radar_domain.settings import get_settings

API = "https://api.github.com"


class _GitHubBase(SourceAdapter):
    """Shared GitHub REST access. Does NOT scan commits (spec §20)."""

    name = "github_base"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "graphics-engine-radar/0.1",
        }
        token = get_settings().github_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _get(self, client: httpx.AsyncClient, url: str, params: dict | None = None):
        for attempt in range(3):
            resp = await client.get(url, params=params)
            if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
                wait = int(resp.headers.get("X-RateLimit-Reset", "0")) - int(time.time())
                await asyncio.sleep(max(2, min(wait, 60)))
                continue
            if resp.status_code >= 500:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp
        resp.raise_for_status()
        raise RuntimeError("github request failed after retries")

    def _repo(self, source: Source) -> str:
        repo = (source.config or {}).get("repo") or source.url
        if not repo:
            raise ValueError(f"github source {source.id} has no repo configured")
        return repo.strip().strip("/")


def _since_epoch_iso(cursor: str | None) -> str | None:
    # cursor format: ISO 8601 timestamp of last successfully seen item
    return cursor


@register
class GitHubReleaseAdapter(_GitHubBase):
    """Fetch published GitHub releases, newest first. Cursor = last release
    published_at ISO timestamp; idempotent because items are deduped by id."""

    name = "github_release"

    async def fetch(self, source: Source, cursor: str | None) -> FetchResult:
        repo = self._repo(source)
        limit = get_settings().collector_max_items_per_fetch
        async with httpx.AsyncClient(base_url=API, headers=self._headers(),
                                     timeout=get_settings().http_timeout_seconds) as client:
            resp = await self._get(client, f"/repos/{repo}/releases",
                                   params={"per_page": min(100, limit), "page": 1})
            releases: list[dict[str, Any]] = resp.json()

        items: list[RawItemDraft] = []
        newest = cursor
        for rel in releases:
            if rel.get("draft"):
                continue
            published = rel.get("published_at") or rel.get("created_at")
            if cursor and published and published <= cursor:
                continue
            body = rel.get("body") or ""
            items.append(RawItemDraft(
                external_id=f"{repo}#release:{rel.get('id')}",
                url=rel.get("html_url"),
                canonical_url=canonical_url(rel.get("html_url")),
                title=rel.get("name") or rel.get("tag_name") or "",
                content=f"{rel.get('name') or rel.get('tag_name')}\n\n{body}".strip(),
                author=(rel.get("author") or {}).get("login"),
                published_at=published,
                raw_payload={
                    "repo": repo, "tag": rel.get("tag_name"),
                    "prerelease": rel.get("prerelease"),
                    "assets": [a.get("name") for a in rel.get("assets", [])][:20],
                },
            ))
            if published and (newest is None or published > newest):
                newest = published
        return FetchResult(items=items, next_cursor=newest,
                           metadata={"repo": repo, "count": len(items)})


@register
class GitHubPRAdapter(_GitHubBase):
    """Fetch merged PRs filtered by keywords/labels/authors per source config
    (spec §20/§7). Cursor = last merged_at ISO timestamp."""

    name = "github_pr"

    async def fetch(self, source: Source, cursor: str | None) -> FetchResult:
        repo = self._repo(source)
        cfg = source.config or {}
        watch = cfg.get("watch") or {}
        pr_cfg = watch.get("pull_requests") or {}
        merged_only = bool(pr_cfg.get("merged_only", True))
        keywords = [k.lower() for k in (pr_cfg.get("keywords") or [])]
        labels = [l.lower() for l in (cfg.get("labels") or pr_cfg.get("labels") or [])]
        authors = set(cfg.get("authors") or pr_cfg.get("authors") or [])
        limit = get_settings().collector_max_items_per_fetch

        async with httpx.AsyncClient(base_url=API, headers=self._headers(),
                                     timeout=get_settings().http_timeout_seconds) as client:
            params: dict[str, Any] = {"per_page": 50, "page": 1,
                                      "sort": "updated", "direction": "desc"}
            if merged_only:
                params["state"] = "closed"
            else:
                params["state"] = "all"
            resp = await self._get(client, f"/repos/{repo}/pulls", params=params)
            pulls: list[dict[str, Any]] = resp.json()

        items: list[RawItemDraft] = []
        newest = cursor
        for pr in pulls:
            merged_at = pr.get("merged_at")
            if merged_only and not merged_at:
                continue
            stamp = merged_at or pr.get("updated_at")
            if cursor and stamp and stamp <= cursor:
                continue
            if authors and pr.get("user", {}).get("login") not in authors:
                continue
            pr_labels = [l["name"].lower() for l in pr.get("labels", [])]
            if labels and not (set(pr_labels) & set(labels)):
                continue
            text = f"{pr.get('title', '')}\n{pr.get('body') or ''}".lower()
            if keywords and not any(k in text for k in keywords):
                continue
            items.append(RawItemDraft(
                external_id=f"{repo}#pr:{pr['number']}",
                url=pr.get("html_url"),
                canonical_url=canonical_url(pr.get("html_url")),
                title=pr.get("title") or "",
                content=f"{pr.get('title', '')}\n\n{pr.get('body') or ''}".strip()[:20000],
                author=pr.get("user", {}).get("login"),
                published_at=merged_at,
                raw_payload={
                    "repo": repo, "number": pr["number"],
                    "labels": pr_labels,
                    "merged_at": merged_at,
                    "additions": pr.get("additions"), "deletions": pr.get("deletions"),
                    "changed_files": pr.get("changed_files"),
                },
            ))
            if stamp and (newest is None or stamp > newest):
                newest = stamp
            if len(items) >= limit:
                break
        return FetchResult(items=items, next_cursor=newest,
                           metadata={"repo": repo, "count": len(items)})


@register
class GitHubIssueAdapter(_GitHubBase):
    name = "github_issue"

    async def fetch(self, source: Source, cursor: str | None) -> FetchResult:
        repo = self._repo(source)
        cfg = source.config or {}
        keywords = [k.lower() for k in cfg.get("keywords", [])]
        async with httpx.AsyncClient(base_url=API, headers=self._headers(),
                                     timeout=get_settings().http_timeout_seconds) as client:
            resp = await self._get(client, f"/repos/{repo}/issues",
                                   params={"state": "all", "per_page": 50, "page": 1,
                                           "sort": "updated", "direction": "desc"})
            issues: list[dict[str, Any]] = resp.json()

        items: list[RawItemDraft] = []
        newest = cursor
        for issue in issues:
            if "pull_request" in issue:
                continue
            stamp = issue.get("updated_at")
            if cursor and stamp and stamp <= cursor:
                continue
            text = f"{issue.get('title', '')}\n{issue.get('body') or ''}".lower()
            if keywords and not any(k in text for k in keywords):
                continue
            items.append(RawItemDraft(
                external_id=f"{repo}#issue:{issue['number']}",
                url=issue.get("html_url"),
                canonical_url=canonical_url(issue.get("html_url")),
                title=issue.get("title") or "",
                content=f"{issue.get('title', '')}\n\n{issue.get('body') or ''}".strip()[:20000],
                author=issue.get("user", {}).get("login"),
                published_at=issue.get("created_at"),
                raw_payload={"repo": repo, "number": issue["number"]},
            ))
            if stamp and (newest is None or stamp > newest):
                newest = stamp
        return FetchResult(items=items, next_cursor=newest,
                           metadata={"repo": repo, "count": len(items)})
