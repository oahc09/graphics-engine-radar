"""Pipeline orchestration (spec §18): RawItem -> Candidate -> Event Retrieval
-> Clustering -> Source Verification -> Technical Analysis -> Topic Mapping
-> Maturity -> Impact -> (Trend Update on demand)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from radar_domain.enums import RawFilterStatus
from radar_domain.models import Event, EventSource, EventTopic, Object, RawItem, Topic
from radar_intelligence import analysis as an
from radar_intelligence import cluster as cl
from radar_intelligence import retrieval as rt
from radar_intelligence.candidate import detect_candidate
from radar_intelligence.embeddings import embed_sync
from radar_intelligence.rule_filter import apply_rule_filter

log = logging.getLogger("intelligence.pipeline")


def _resolve_object(session: Session, raw: RawItem):
    """For discovery-ish sources (community/technical media), the item may
    actually be about another monitored object (e.g. a Vulkan spec release
    reported on a Linux news feed). Prefer the object explicitly named in the
    title (longest match wins)."""
    source = raw.source
    object_ = source.object
    # only vendor/platform discovery feeds get retargeted: an engine's own
    # blog/release is about that engine even if the title mentions an API
    if object_.type not in ("gpu_vendor", "platform"):
        return object_
    title_l = (raw.title or "").lower()
    best, best_len = object_, 0
    for obj in session.query(Object).filter(Object.active.is_(True)).all():
        for cand in [obj.name] + list(obj.aliases or []):
            cand_l = cand.lower().strip()
            if len(cand_l) < 4 or cand_l == object_.name.lower():
                continue
            if cand_l in title_l and len(cand_l) > best_len and obj.id != object_.id:
                best, best_len = obj, len(cand_l)
    return best


async def process_candidate(session: Session, raw: RawItem) -> dict:
    result = {"raw_item": str(raw.id), "object": raw.source.object.slug, "outcome": None}

    object_ = _resolve_object(session, raw)
    source = raw.source
    decision = await detect_candidate(raw, raw.source.object, source)
    if not decision.candidate:
        raw.filter_status = RawFilterStatus.IGNORED.value
        raw.filter_reason = f"candidate:no:{decision.reason[:300]}"
        result["outcome"] = "not_candidate"
        return result

    raw.filter_status = RawFilterStatus.CANDIDATE.value
    raw.filter_reason = f"candidate:yes:{decision.reason[:300]}"

    # --- Event Retrieval (spec §22) ---
    change_text = f"{raw.title}\n{(raw.content or '')[:2000]}"
    similar = rt.retrieve_similar_events(session, raw.title, change_text, object_.slug)

    merged_event = None
    merge_reason = None
    for hit in similar:
        cluster_decision = await cl.decide_cluster(hit["similarity"], hit["event"], raw, source)
        if cluster_decision.same_event:
            merged_event = hit["event"]
            merge_reason = cluster_decision.reason
            break

    if merged_event is not None:
        # --- attach as evidence of existing event (multi-source merge) ---
        cl.attach_source_to_event(session, merged_event, raw,
                                  cl.ROLE_BY_SOURCE_TYPE.get(source.type, "supporting"))
        cl.ensure_primary_source(session, merged_event)
        merged_event.updated_at = datetime.now(timezone.utc)
        result["outcome"] = "merged"
        result["event_slug"] = merged_event.slug
        result["merge_reason"] = merge_reason
        return result

    # --- new Event + Technical Analysis (spec §24) ---
    related_titles = [h["event"].title for h in similar[:3]]
    event = Event(
        slug=cl.make_event_slug(object_.slug, raw.title),
        title=(raw.title or "(untitled)")[:200],
        object_id=object_.id,
        status="candidate",
        event_type="FEATURE_ADDED",
        change_signal="NEW",
    )
    session.add(event)
    session.flush()

    evt_analysis = await an.analyze_technical(object_, [raw], related_titles)
    event.title = evt_analysis.title[:250] or event.title
    event.summary = evt_analysis.summary
    event.change = evt_analysis.what_changed
    event.why_it_matters = evt_analysis.why_it_matters
    event.who_should_care = evt_analysis.who_should_care
    event.event_type = evt_analysis.event_type
    event.change_signal = evt_analysis.change_signal
    event.maturity_from = evt_analysis.maturity_from
    event.maturity_to = evt_analysis.maturity_to
    event.confidence = evt_analysis.confidence
    event.title_embedding, event.change_embedding = an.embed_event(
        event.title, f"{evt_analysis.what_changed} {evt_analysis.summary}")
    event.published_at = raw.published_at or raw.fetched_at

    # --- Topic Mapping (spec §15) ---
    topic_rows = session.query(Topic).all()
    mapping = await an.map_topics(event.title, event.summary, evt_analysis.what_changed, topic_rows)
    slug_to_topic = {t.slug: t for t in topic_rows}
    for assign in mapping.topics[:5]:
        topic = slug_to_topic.get(assign.slug)
        if topic is None:
            continue
        session.add(EventTopic(event_id=event.id, topic_id=topic.id,
                               relation=assign.relation, confidence=assign.confidence))

    # --- Impact Evaluation (spec §17) ---
    impact = await an.evaluate_impact(evt_analysis)
    event.impact_capability = impact.capability
    event.impact_engineering = impact.engineering
    event.impact_adoption = impact.adoption
    event.impact_scope = impact.scope
    event.impact_confidence = impact.evidence
    event.impact_level = impact.impact_level

    # --- Source Verification: attach evidence, pick primary (spec §2.3) ---
    cl.attach_source_to_event(session, event, raw,
                              cl.ROLE_BY_SOURCE_TYPE.get(source.type, "supporting"))
    cl.ensure_primary_source(session, event)
    has_primary = session.query(EventSource).filter_by(
        event_id=event.id, role="primary").count() > 0
    event.status = "verified" if has_primary else "candidate"

    raw.filter_status = RawFilterStatus.PROCESSED.value
    raw.filter_reason = f"event:{event.slug}"
    result["outcome"] = "created"
    result["event_slug"] = event.slug
    result["impact"] = impact.impact_level
    return result


async def run_intelligence(session: Session, limit: int | None = None) -> dict:
    """Full intelligence pass over pending RawItems."""
    filter_stats = apply_rule_filter(session)
    q = session.query(RawItem).filter(RawItem.filter_status == RawFilterStatus.NEW.value)
    if limit:
        q = q.limit(limit)
    raws = q.all()
    outcomes = {"created": 0, "merged": 0, "not_candidate": 0, "error": 0}
    details = []
    for raw in raws:
        try:
            r = await process_candidate(session, raw)
            session.commit()
            outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
            details.append(r)
        except Exception as exc:  # one item failing must not stop the pass
            session.rollback()
            outcomes["error"] += 1
            log.exception("failed processing raw item %s", raw.id)
            details.append({"raw_item": str(raw.id), "outcome": "error",
                            "error": f"{type(exc).__name__}: {exc}"})
    return {"filter": filter_stats, "processed": len(raws),
            "outcomes": outcomes, "details": details}


def run_intelligence_sync(session: Session, limit: int | None = None) -> dict:
    return asyncio.run(run_intelligence(session, limit))
