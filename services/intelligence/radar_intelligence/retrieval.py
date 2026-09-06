"""Event Retrieval (spec §22 / M7): before analyzing a candidate, look for
similar existing Events in the past 30-90 days using pgvector cosine distance
over title/change embeddings plus object/topic/alias overlap."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from radar_domain.models import Event
from radar_intelligence.embeddings import cosine, embed_sync


def retrieve_similar_events(session: Session, title: str, change_text: str,
                            object_slug: str | None = None,
                            window_days: int = 90, top_k: int = 5) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    q = (
        session.query(Event)
        .filter(Event.status.notin_(("rejected", "merged")))
        .filter(Event.first_seen_at >= cutoff)
    )
    if object_slug:
        from radar_domain.models import Object
        obj = session.scalar(select(Object).where(Object.slug == object_slug))
        if obj is not None:
            q = q.filter(Event.object_id == obj.id)
    candidates = q.order_by(Event.first_seen_at.desc()).limit(200).all()
    if not candidates:
        return []

    title_vec = embed_sync(title)
    change_vec = embed_sync(change_text)
    results = []
    for event in candidates:
        sim_title = cosine(title_vec, event.title_embedding or [])
        sim_change = cosine(change_vec, event.change_embedding or [])
        combined = max(sim_title, 0.6 * sim_change + 0.4 * sim_title)
        results.append({
            "event": event,
            "sim_title": round(sim_title, 4),
            "sim_change": round(sim_change, 4),
            "similarity": round(combined, 4),
        })
    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results[:top_k]
