"""Event Clustering (spec §23 / M7): deterministic rules + embedding
similarity + LLM final judgment. Official sources are preferred as primary
(spec §2.3)."""

from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from radar_intelligence.llm import run_llm_stage
from radar_intelligence.retrieval import retrieve_similar_events
from radar_prompts import EVENT_CLUSTERING_PROMPT, PROMPT_VERSIONS, SYSTEM_GRAPHICS_ANALYST

# role ranking: lower is stronger; primary = strongest evidence available
ROLE_RANK = {"primary": 0, "official": 1, "supporting": 2, "community": 3, "discovery": 4}

ROLE_BY_SOURCE_TYPE = {
    "release_notes": "official",
    "spec_registry": "official",
    "official_blog": "official",
    "github_release": "official",
    "github_pr": "supporting",
    "github_issue": "community",
    "github_discussion": "community",
    "rss": "supporting",
    "community": "community",
    "html": "supporting",
    "documentation": "supporting",
    "roadmap": "official",
    "conference": "official",
}

VERSION_TAG_RE = re.compile(r"\b(v?\d+\.\d+(\.\d+)?)\b", re.I)

SIMILARITY_THRESHOLD = 0.62


class ClusterDecision(BaseModel):
    same_event: bool
    confidence: float = 0.5
    reason: str = ""


def _tag_of(title: str) -> str | None:
    m = VERSION_TAG_RE.search(title or "")
    return m.group(1) if m else None


def heuristic_cluster_match(similarity: float, event, raw, source) -> ClusterDecision:
    # Deterministic rule: same object + same version tag in title => same event
    etag, rtag = _tag_of(event.title or ""), _tag_of(raw.title or "")
    if etag and rtag and etag == rtag and event.object_id == raw.source.object_id:
        return ClusterDecision(same_event=True, confidence=0.95,
                               reason=f"same object and version tag {etag}")
    if similarity >= SIMILARITY_THRESHOLD:
        return ClusterDecision(same_event=True, confidence=min(0.9, similarity),
                               reason=f"embedding similarity {similarity:.2f} >= {SIMILARITY_THRESHOLD}")
    return ClusterDecision(same_event=False, confidence=0.5,
                           reason=f"similarity {similarity:.2f} below threshold")


async def decide_cluster(similarity: float, event, raw, source) -> ClusterDecision:
    heuristic = heuristic_cluster_match(similarity, event, raw, source)
    # Ambiguous band -> LLM final judgment (spec §23). High-confidence rules
    # skip the LLM to keep cost proportional.
    if 0.45 <= similarity < 0.75 and not heuristic.same_event:
        from radar_intelligence.llm import input_hash, record_ai_execution
        input_payload = {
            "event_title": event.title, "event_summary": event.summary,
            "item_title": raw.title, "item_content": (raw.content or "")[:2000],
            "object": raw.source.object.slug, "source_type": source.type,
        }
        decision, _ = await run_llm_stage(
            "event_clustering", PROMPT_VERSIONS["event_clustering"], input_payload,
            SYSTEM_GRAPHICS_ANALYST,
            EVENT_CLUSTERING_PROMPT.format(
                event_title=event.title, event_summary=event.summary,
                event_objects=str(event.object_id), event_published=str(event.published_at),
                source_type=source.type, object_name=raw.source.object.name,
                title=raw.title, content=(raw.content or "")[:3000]),
            ClusterDecision,
        )
        if decision is not None:
            return ClusterDecision.model_validate(decision)
        record_ai_execution("event_clustering", "heuristic-rules",
                            PROMPT_VERSIONS["event_clustering"],
                            input_hash(input_payload), input_payload,
                            heuristic.model_dump(), success=True)
    return heuristic


def attach_source_to_event(session: Session, event, raw, role: str) -> bool:
    """Attach raw item as evidence. Returns True if this is a new merge."""
    from radar_domain.models import EventSource

    existing = session.query(EventSource).filter_by(
        event_id=event.id, raw_item_id=raw.id).first()
    if existing:
        return False
    source_type = raw.source.type
    role = ROLE_BY_SOURCE_TYPE.get(source_type, "supporting")
    # downgrade from primary if no official evidence backs it yet
    if role in ("official", "primary"):
        role = "official"
    link = EventSource(event_id=event.id, raw_item_id=raw.id, role=role, confidence=0.8)
    session.add(link)
    raw.filter_status = "processed"
    raw.filter_reason = f"event_evidence:{event.slug}"
    return True


def ensure_primary_source(session: Session, event) -> None:
    """Promote the best-ranked source to primary (official first, spec §2.3)."""
    from radar_domain.models import EventSource

    links = session.query(EventSource).filter_by(event_id=event.id).all()
    if not links:
        return
    best = min(links, key=lambda l: ROLE_RANK.get(l.role, 9))
    if best.role != "primary":
        for link in links:
            if link.role == "primary":
                link.role = "official"
        best.role = "primary"


def make_event_slug(object_slug: str, title: str) -> str:
    import hashlib
    from datetime import date

    digest = hashlib.sha1(f"{title}".encode("utf-8")).hexdigest()[:8]
    return f"{object_slug}-{date.today().isoformat()}-{digest}"
