"""FastAPI backend (spec §19 / M10): events, selected, objects, topics,
trends, digests with filters."""

from __future__ import annotations

from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from radar_domain.db import get_session, init_extensions
from radar_domain.models import Event, EventSource, EventTopic, Object, RawItem, Source, Topic
from radar_intelligence.digest import select_for_homepage
from radar_intelligence.trend import topic_latest_trends
from radar_api.admin import admin

app = FastAPI(title="Graphics Engine Radar API", version="0.1.0")
app.include_router(admin)


@app.on_event("startup")
def _startup() -> None:
    try:
        init_extensions()
    except Exception:
        pass


def _event_dict(session: Session, event: Event, with_sources: bool = True) -> dict:
    data = {
        "id": str(event.id),
        "slug": event.slug,
        "title": event.title,
        "summary": event.summary,
        "event_type": event.event_type,
        "change_signal": event.change_signal,
        "change": event.change,
        "why_it_matters": event.why_it_matters,
        "who_should_care": event.who_should_care,
        "impact_level": event.impact_level,
        "confidence": event.confidence,
        "maturity_from": event.maturity_from,
        "maturity_to": event.maturity_to,
        "first_seen_at": event.first_seen_at.isoformat() if event.first_seen_at else None,
        "published_at": event.published_at.isoformat() if event.published_at else None,
        "status": event.status,
        "object_slug": event.object.slug if event.object else None,
        "topics": [
            {"slug": et.topic.slug, "name": et.topic.name, "relation": et.relation}
            for et in event.topics
        ],
    }
    if with_sources:
        links = (
            session.query(EventSource, RawItem, Source)
            .join(RawItem, EventSource.raw_item_id == RawItem.id)
            .join(Source, RawItem.source_id == Source.id)
            .filter(EventSource.event_id == event.id)
            .all()
        )
        data["sources"] = [
            {
                "role": link.role,
                "type": src.type,
                "url": raw.url,
                "title": raw.title,
                "published_at": raw.published_at.isoformat() if raw.published_at else None,
            }
            for link, raw, src in links
        ]
    return data


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/events")
def list_events(
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    domain: str | None = None,
    object_slug: str | None = None,
    topic: str | None = None,
    event_type: str | None = None,
    impact: str | None = None,
    platform: str | None = None,
    change_signal: str | None = None,
    since: str | None = None,
    until: str | None = None,
    q: str | None = None,
) -> dict:
    query = session.query(Event).filter(~Event.status.in_(("rejected", "merged")))
    joined_object = False
    if event_type:
        query = query.filter(Event.event_type == event_type.upper())
    if impact:
        query = query.filter(Event.impact_level == impact.capitalize())
    if change_signal:
        query = query.filter(Event.change_signal == change_signal.upper())
    if object_slug or domain:
        query = query.join(Object, Event.object_id == Object.id)
        joined_object = True
    if object_slug:
        query = query.filter(Object.slug == object_slug)
    if domain:
        query = query.filter(Object.domain == domain)
    if topic:
        query = query.join(EventTopic, EventTopic.event_id == Event.id).join(
            Topic, EventTopic.topic_id == Topic.id).filter(Topic.slug == topic)
    if platform:
        like = f"%{platform.lower()}%"
        query = query.filter(func.lower(Event.change).like(like) | func.lower(Event.summary).like(like))
    if since:
        query = query.filter(Event.first_seen_at >= since)
    if until:
        query = query.filter(Event.first_seen_at <= until)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(or_(func.lower(Event.title).like(like),
                                 func.lower(Event.summary).like(like)))
    total = query.count()
    events = (
        query.options(joinedload(Event.object), joinedload(Event.topics))
        .order_by(Event.first_seen_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"total": total, "page": page, "page_size": page_size,
            "events": [_event_dict(session, e, with_sources=False) for e in events]}


@app.get("/events/{slug}")
def get_event(slug: str, session: Session = Depends(get_session)) -> dict:
    event = session.query(Event).filter(Event.slug == slug).first()
    if event is None:
        raise HTTPException(404, "event not found")
    return _event_dict(session, event)


@app.get("/selected")
def selected(session: Session = Depends(get_session)) -> dict:
    events = select_for_homepage(session)
    return {"count": len(events),
            "events": [_event_dict(session, e) for e in events[:30]]}


@app.get("/objects")
def list_objects(
    session: Session = Depends(get_session),
    type: str | None = None,
    domain: str | None = None,
) -> dict:
    query = session.query(Object).filter(Object.active.is_(True))
    if type:
        query = query.filter(Object.type == type)
    if domain:
        query = query.filter(Object.domain == domain)
    objs = query.order_by(Object.type, Object.name).all()
    return {
        "count": len(objs),
        "objects": [
            {"slug": o.slug, "name": o.name, "type": o.type, "domain": o.domain,
             "description": o.description, "official_url": o.official_url,
             "github_repo": o.github_repo}
            for o in objs
        ],
    }


@app.get("/objects/{slug}")
def get_object(slug: str, session: Session = Depends(get_session)) -> dict:
    obj = session.query(Object).filter(Object.slug == slug).first()
    if obj is None:
        raise HTTPException(404, "object not found")
    events = (
        session.query(Event)
        .filter(Event.object_id == obj.id, ~Event.status.in_(("rejected", "merged")))
        .order_by(Event.first_seen_at.desc())
        .limit(50)
        .all()
    )
    sources = session.query(Source).filter(Source.object_id == obj.id).all()
    return {
        "slug": obj.slug, "name": obj.name, "type": obj.type, "domain": obj.domain,
        "description": obj.description, "official_url": obj.official_url,
        "github_repo": obj.github_repo, "aliases": obj.aliases,
        "sources": [{"type": s.type, "url": s.url, "adapter": s.adapter,
                     "enabled": s.enabled,
                     "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
                     "last_error": s.last_error}
                    for s in sources],
        "events": [_event_dict(session, e, with_sources=False) for e in events],
    }


@app.get("/topics")
def list_topics(session: Session = Depends(get_session)) -> dict:
    topics = session.query(Topic).order_by(Topic.name).all()
    counts = dict(
        session.query(Topic.slug, func.count(EventTopic.id))
        .join(EventTopic, EventTopic.topic_id == Topic.id)
        .group_by(Topic.slug)
        .all()
    )
    return {"count": len(topics),
            "topics": [{"slug": t.slug, "name": t.name, "parent": t.parent_slug,
                        "description": t.description, "event_count": counts.get(t.slug, 0)}
                       for t in topics]}


@app.get("/topics/{slug}")
def get_topic(slug: str, session: Session = Depends(get_session)) -> dict:
    topic = session.query(Topic).filter(Topic.slug == slug).first()
    if topic is None:
        raise HTTPException(404, "topic not found")
    events = (
        session.query(Event)
        .join(EventTopic, EventTopic.event_id == Event.id)
        .filter(EventTopic.topic_id == topic.id, ~Event.status.in_(("rejected", "merged")))
        .order_by(Event.first_seen_at.desc())
        .limit(100)
        .all()
    )
    trends = {t["topic_slug"]: t for t in topic_latest_trends(session)}
    return {
        "slug": topic.slug, "name": topic.name, "description": topic.description,
        "trend": trends.get(slug),
        "events": [_event_dict(session, e, with_sources=False) for e in events],
    }


@app.get("/trends")
def trends(session: Session = Depends(get_session)) -> dict:
    return {"trends": topic_latest_trends(session)}


@app.get("/digests/{kind}")
def get_digest(kind: Literal["daily", "weekly", "monthly"],
               session: Session = Depends(get_session)) -> dict:
    from radar_domain.models import DailyDigest

    digest = session.query(DailyDigest).filter(DailyDigest.kind == kind).one_or_none()
    if digest is None:
        raise HTTPException(404, f"no {kind} digest generated yet")
    return {"kind": kind, "date": digest.date.isoformat(), "title": digest.title,
            "body": digest.body, "event_ids": digest.event_ids}


@app.get("/metrics")
def metrics(session: Session = Depends(get_session)) -> dict:
    raw_total = session.query(func.count(RawItem.id)).scalar()
    ignored = session.query(func.count(RawItem.id)).filter(
        RawItem.filter_status == "ignored").scalar()
    candidates = session.query(func.count(RawItem.id)).filter(
        RawItem.filter_status == "candidate").scalar()
    event_total = session.query(func.count(Event.id)).scalar()
    selected = session.query(func.count(Event.id)).filter(
        Event.impact_level.in_(("High", "Critical"))).scalar()
    links = session.query(func.count(EventSource.id)).scalar()
    events_with_evidence = session.query(
        func.count(func.distinct(EventSource.event_id))).scalar()
    official_events = (
        session.query(func.count(func.distinct(EventSource.event_id)))
        .join(RawItem, EventSource.raw_item_id == RawItem.id)
        .join(Source, RawItem.source_id == Source.id)
        .filter(Source.type.in_(("github_release", "release_notes", "spec_registry",
                                 "official_blog")))
        .scalar()
    )
    return {
        "raw_item_total": raw_total,
        "ignored": ignored,
        "candidate": candidates,
        "event_total": event_total,
        "selected": selected,
        "evidence_links": links,
        "duplicate_merges": max(0, links - events_with_evidence),
        "events_with_official_source": official_events,
        "official_source_ratio": round(official_events / events_with_evidence, 3)
        if events_with_evidence else 0.0,
    }
