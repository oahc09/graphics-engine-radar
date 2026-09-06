"""Trend Engine (spec §25 / M12): explainable rule-based trend states per
topic from 30d/90d event statistics. Never uses page views or popularity."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from radar_domain.enums import TrendState
from radar_domain.models import Event, EventTopic, Object, TrendSnapshot


def _stats(session: Session, topic_id, days: int) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        session.query(Event, EventTopic)
        .join(EventTopic, EventTopic.event_id == Event.id)
        .filter(EventTopic.topic_id == topic_id)
        .filter(Event.status.notin_(("rejected", "merged")))
        .filter(Event.first_seen_at >= cutoff)
        .all()
    )
    events = [e for e, _ in rows]
    object_ids = {e.object_id for e in events if e.object_id}
    domains = Counter()
    vendors = 0
    for oid in object_ids:
        obj = session.get(Object, oid)
        if obj is None:
            continue
        domains[obj.domain] += 1
        if obj.domain == "gpu_platform":
            vendors += 1
    maturity_transitions = sum(
        1 for e in events
        if e.maturity_from and e.maturity_to and e.maturity_from != e.maturity_to)
    adoptions = sum(1 for e in events if e.change_signal == "ADOPT")
    important = sum(1 for e in events if e.impact_level in ("High", "Critical"))
    platform_expansions = sum(1 for e in events if e.change_signal == "EXPAND")
    return {
        "event_count": len(events),
        "important_event_count": important,
        "unique_object_count": len(object_ids),
        "unique_vendor_count": vendors,
        "maturity_transition_count": maturity_transitions,
        "adoption_count": adoptions,
        "platform_expansion_count": platform_expansions,
    }


def _state(s30: dict, s90: dict) -> str:
    important = s30["important_event_count"]
    if s30["event_count"] == 0:
        return TrendState.COOLING.value if s90["event_count"] == 0 else TrendState.STABLE.value
    maturity = s30["maturity_transition_count"]
    if important >= 5 and (s30["event_count"] >= 1.5 * max(1, s90["event_count"] // 3)):
        return TrendState.ACCELERATING.value
    if maturity >= 2 or important >= 3:
        return TrendState.ACCELERATING.value if important >= 4 else TrendState.GROWING.value
    if important >= 1 or s30["event_count"] >= 3:
        return TrendState.GROWING.value
    if s90["event_count"] > 0 and important == 0:
        return TrendState.STABLE.value
    return TrendState.COOLING.value


def update_trends(session: Session) -> int:
    """Recompute TrendSnapshots for all topics (30d and 90d windows)."""
    today = datetime.now(timezone.utc).date()
    topic_ids = [tid for (tid,) in session.query(EventTopic.topic_id).distinct().all()]
    updated = 0
    for topic_id in topic_ids:
        s30 = _stats(session, topic_id, 30)
        s90 = _stats(session, topic_id, 90)
        state = _state(s30, s90)
        # upsert snapshots (unique: topic_id, window_days, snapshot_date)
        for window, stats in ((30, s30), (90, s90)):
            snap = (
                session.query(TrendSnapshot)
                .filter(
                    TrendSnapshot.topic_id == topic_id,
                    TrendSnapshot.window_days == window,
                    func.date(TrendSnapshot.snapshot_date) == today,
                )
                .one_or_none()
            )
            if snap is None:
                snap = TrendSnapshot(topic_id=topic_id, window_days=window,
                                     snapshot_date=datetime.now(timezone.utc))
                session.add(snap)
            for key in ("event_count", "important_event_count", "unique_object_count",
                        "unique_vendor_count", "platform_expansion_count",
                        "maturity_transition_count", "adoption_count"):
                setattr(snap, key, stats[key])
            snap.state = state
            updated += 1
    session.commit()
    return updated


def topic_latest_trends(session: Session) -> list[dict]:
    from radar_domain.models import Topic

    out = []
    topics = session.query(Topic).all()
    for topic in topics:
        snap = (
            session.query(TrendSnapshot)
            .filter(TrendSnapshot.topic_id == topic.id, TrendSnapshot.window_days == 30)
            .order_by(TrendSnapshot.snapshot_date.desc())
            .first()
        )
        if snap is None:
            continue
        out.append({
            "topic_slug": topic.slug,
            "topic_name": topic.name,
            "state": snap.state,
            "event_count_30d": snap.event_count,
            "important_event_count_30d": snap.important_event_count,
            "unique_object_count_30d": snap.unique_object_count,
            "maturity_transition_count_30d": snap.maturity_transition_count,
            "adoption_count_30d": snap.adoption_count,
        })
    out.sort(key=lambda t: (t["important_event_count_30d"], t["event_count_30d"]), reverse=True)
    return out
