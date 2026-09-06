"""Config-driven monitoring setup (spec §31/§32).

Loads config/objects/*.yaml, config/sources/*.yaml, config/topics/*.yaml into
the database. Adding a monitored object is adding a YAML file, not code.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from radar_domain.enums import ObjectType, SourceType
from radar_domain.models import Object, Source, Topic

_ADAPTER_BY_SOURCE_TYPE: dict[str, str] = {
    SourceType.GITHUB_RELEASE.value: "github_release",
    SourceType.GITHUB_PR.value: "github_pr",
    SourceType.GITHUB_ISSUE.value: "github_issue",
    SourceType.GITHUB_DISCUSSION.value: "github_discussion",
    SourceType.RSS.value: "rss",
    SourceType.RELEASE_NOTES.value: "release_notes",
    SourceType.OFFICIAL_BLOG.value: "rss",
    SourceType.SPEC_REGISTRY.value: "spec_registry",
    SourceType.DOCUMENTATION.value: "html",
    SourceType.ROADMAP.value: "html",
    SourceType.CONFERENCE.value: "html",
    SourceType.COMMUNITY.value: "rss",
    SourceType.HTML.value: "html",
}


def _load_yaml_dir(directory: Path) -> list[dict]:
    docs: list[dict] = []
    if not directory.exists():
        return docs
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["_file"] = path.name
            docs.append(data)
        elif isinstance(data, list):
            docs.extend(item for item in data if isinstance(item, dict))
    return docs


def load_object_configs(config_dir: Path) -> list[dict]:
    return _load_yaml_dir(config_dir / "objects")


def load_source_configs(config_dir: Path) -> list[dict]:
    return _load_yaml_dir(config_dir / "sources")


def load_topic_configs(config_dir: Path) -> list[dict]:
    return _load_yaml_dir(config_dir / "topics")


def sync_objects(session: Session, config_dir: Path) -> tuple[int, int]:
    created, updated = 0, 0
    for cfg in load_object_configs(config_dir):
        slug = cfg["id"]
        obj = session.scalar(select(Object).where(Object.slug == slug))
        if obj is None:
            obj = Object(slug=slug)
            session.add(obj)
            created += 1
        obj.name = cfg.get("name", slug)
        obj.type = cfg.get("type", ObjectType.TECHNOLOGY.value)
        obj.domain = cfg.get("domain", "rendering_tech")
        obj.description = cfg.get("description", "")
        obj.official_url = cfg.get("official_url")
        obj.github_repo = cfg.get("github_repo")
        obj.aliases = cfg.get("aliases", [])
        obj.active = bool(cfg.get("active", True))
        updated += 1
    session.flush()
    return created, updated


def sync_topics(session: Session, config_dir: Path) -> tuple[int, int]:
    created, updated = 0, 0
    for cfg in load_topic_configs(config_dir):
        slug = cfg["id"]
        topic = session.scalar(select(Topic).where(Topic.slug == slug))
        if topic is None:
            topic = Topic(slug=slug)
            session.add(topic)
            created += 1
        topic.name = cfg.get("name", slug)
        topic.parent_slug = cfg.get("parent")
        topic.description = cfg.get("description", "")
        topic.aliases = cfg.get("aliases", [])
        topic.keywords = cfg.get("keywords", [])
        updated += 1
    session.flush()
    return created, updated


def sync_sources(session: Session, config_dir: Path) -> tuple[int, int]:
    """Object-level source configs (objects may declare inline `sources`) plus
    standalone config/sources entries. A source is keyed by
    (object_slug, adapter, url-or-repo) so re-syncing is idempotent."""
    created, updated = 0, 0

    entries: list[tuple[str, dict]] = []
    for cfg in load_object_configs(config_dir):
        for src in cfg.get("sources", []) or []:
            entries.append((cfg["id"], src))
    standalone = load_source_configs(config_dir)
    obj_by_slug: dict[str, Object | None] = {}

    def get_object(slug: str) -> Object | None:
        if slug not in obj_by_slug:
            obj_by_slug[slug] = session.scalar(select(Object).where(Object.slug == slug))
        return obj_by_slug[slug]

    for obj_slug, src in entries:
        obj = get_object(obj_slug)
        if obj is None:
            continue
        stype = src.get("type")
        if stype not in SourceType.__members__ and stype not in [e.value for e in SourceType]:
            continue
        url = src.get("url")
        repo = src.get("repo")
        adapter = _ADAPTER_BY_SOURCE_TYPE.get(stype, "html")
        # stable identity for the source row
        external_key = repo if repo else (url or "")
        if not external_key:
            continue
        existing = session.scalar(
            select(Source).where(
                Source.object_id == obj.id,
                Source.adapter == adapter,
                Source.url == external_key,
            )
        )
        if existing is None:
            existing = Source(object_id=obj.id, adapter=adapter, url=external_key)
            session.add(existing)
            created += 1
        existing.type = stype
        cfg = {k: v for k, v in src.items() if k not in ("type", "url", "repo")}
        existing.config = cfg or {}
        existing.poll_interval_minutes = int(src.get("poll_interval", 120))
        existing.enabled = bool(src.get("enabled", True))
        updated += 1

    session.flush()
    return created, updated


def sync_all(session: Session, config_dir: Path) -> dict:
    o_created, o_total = sync_objects(session, config_dir)
    t_created, t_total = sync_topics(session, config_dir)
    s_created, s_total = sync_sources(session, config_dir)
    return {
        "objects": {"created": o_created, "total": o_total},
        "topics": {"created": t_created, "total": t_total},
        "sources": {"created": s_created, "total": s_total},
    }
