"""Minimal admin/feedback endpoints (spec §37 / plan §25).

Purpose is recording where AI judgment was wrong (feedback dataset), not a CMS:
promote / reject / merge / edit / override impact / edit topic mapping.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from radar_domain.db import get_session
from radar_domain.models import Event, EventSource, EventTopic, RawItem


def _get_event(session: Session, slug: str) -> Event:
    event = session.query(Event).filter(Event.slug == slug).first()
    if event is None:
        raise HTTPException(404, "event not found")
    return event


admin = APIRouter(prefix="/admin", tags=["admin"])


class EventEdit(BaseModel):
    title: str | None = None
    summary: str | None = None
    change: str | None = None
    why_it_matters: str | None = None
    impact_level: str | None = None  # Override Impact
    impact_capability: int | None = None
    impact_engineering: int | None = None
    impact_adoption: int | None = None
    impact_scope: int | None = None
    impact_confidence: int | None = None
    maturity_from: str | None = None
    maturity_to: str | None = None


@admin.post("/events/{slug}/promote")
def promote_event(slug: str, session: Session = Depends(get_session)) -> dict:
    event = _get_event(session, slug)
    event.status = "published"
    event.impact_level = max(event.impact_level, "High",
                             key=lambda lv: ("Critical", "High", "Notable").index(lv))
    event.updated_at = datetime.now(timezone.utc)
    session.commit()
    return {"ok": True, "status": event.status, "impact_level": event.impact_level}


@admin.post("/events/{slug}/reject")
def reject_event(slug: str, session: Session = Depends(get_session)) -> dict:
    event = _get_event(session, slug)
    event.status = "rejected"
    session.commit()
    return {"ok": True, "status": event.status}


@admin.post("/events/{slug}/merge-into/{target_slug}")
def merge_event(slug: str, target_slug: str,
                session: Session = Depends(get_session)) -> dict:
    """Manual merge: move evidence links to target and mark source merged."""
    event = _get_event(session, slug)
    target = _get_event(session, target_slug)
    if event.id == target.id:
        raise HTTPException(400, "cannot merge event into itself")
    links = session.query(EventSource).filter_by(event_id=event.id).all()
    for link in links:
        dup = session.query(EventSource).filter_by(
            event_id=target.id, raw_item_id=link.raw_item_id).first()
        if dup:
            session.delete(link)
        else:
            link.event_id = target.id
    raws = session.query(RawItem).filter(
        RawItem.filter_reason == f"event:{event.slug}").all()
    for raw in raws:
        raw.filter_reason = f"event:{target.slug}"
    event.status = "merged"
    target.updated_at = datetime.now(timezone.utc)
    session.commit()
    return {"ok": True, "merged_into": target.slug, "moved_links": len(links)}


@admin.patch("/events/{slug}")
def edit_event(slug: str, payload: EventEdit,
               session: Session = Depends(get_session)) -> dict:
    event = _get_event(session, slug)
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(event, key, value)
    event.updated_at = datetime.now(timezone.utc)
    session.commit()
    return {"ok": True, "updated": list(data.keys())}


@admin.delete("/events/{slug}/topics/{topic_slug}")
def remove_topic(slug: str, topic_slug: str,
                 session: Session = Depends(get_session)) -> dict:
    from radar_domain.models import Topic

    event = _get_event(session, slug)
    topic = session.query(Topic).filter(Topic.slug == topic_slug).first()
    if topic is None:
        raise HTTPException(404, "topic not found")
    link = session.query(EventTopic).filter_by(
        event_id=event.id, topic_id=topic.id).first()
    if link is None:
        raise HTTPException(404, "topic not assigned")
    session.delete(link)
    session.commit()
    return {"ok": True}


@admin.post("/events/{slug}/topics/{topic_slug}")
def add_topic(slug: str, topic_slug: str,
              session: Session = Depends(get_session)) -> dict:
    from radar_domain.models import Topic

    event = _get_event(session, slug)
    topic = session.query(Topic).filter(Topic.slug == topic_slug).first()
    if topic is None:
        raise HTTPException(404, "topic not found")
    exists = session.query(EventTopic).filter_by(
        event_id=event.id, topic_id=topic.id).first()
    if not exists:
        session.add(EventTopic(event_id=event.id, topic_id=topic.id,
                               relation="direct", confidence=1.0))
        session.commit()
    return {"ok": True}
