"""Digest generation (spec §28 / M12): daily/weekly/monthly.

Weekly and monthly re-analyze the whole window; they never concatenate dailies.
Count is dynamic — 宁少勿水 (spec §26).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from radar_domain.models import DailyDigest, Event, EventSource, Object
from radar_intelligence.llm import input_hash, record_ai_execution, run_llm_stage
from radar_prompts import DIGEST_PROMPT, PROMPT_VERSIONS, SYSTEM_GRAPHICS_ANALYST

WINDOW_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}

SELECT_RULES = """A Selected event must satisfy at least one of (spec §26):
- creates a new capability, changes architecture
- enters a new platform or a new engine
- specification change
- significant performance change
- maturity transition
- cross-vendor adoption
- trend inflection signal
"""


def _window_events(session: Session, kind: str) -> list[Event]:
    days = WINDOW_DAYS.get(kind, 1)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        session.query(Event)
        .filter(Event.status.notin_(("rejected", "merged")))
        .filter(Event.first_seen_at >= cutoff)
        .order_by(Event.first_seen_at.desc())
        .limit(5000)
        .all()
    )


def select_for_homepage(session: Session, as_of: datetime | None = None) -> list[Event]:
    """Homepage selection: rule-based, no fixed count, 宁少勿水."""
    events = _window_events(session, "monthly")
    selected = []
    for e in events:
        rule_hit = (
            (e.maturity_from and e.maturity_to and e.maturity_from != e.maturity_to)
            or e.event_type in ("ARCHITECTURE_CHANGE", "SPEC_CHANGE", "BREAKING_CHANGE",
                                "CAPABILITY_ENABLED")
            or e.change_signal in ("EXPAND", "MATURE")
            or e.impact_level in ("High", "Critical")
        )
        if rule_hit:
            selected.append(e)
    return selected


class DigestOutput(BaseModel):
    title: str
    body: str


def _event_lines(events: list[Event]) -> str:
    lines = []
    for e in events:
        primary = None
        for link in e.sources:
            if link.role == "primary":
                primary = link.raw_item
                break
        src = primary.url if primary else ""
        lines.append(
            f"- [{e.impact_level}] ({e.event_type}/{e.change_signal}) {e.title}\n"
            f"  what changed: {e.change}\n"
            f"  why it matters: {e.why_it_matters}\n"
            f"  maturity: {e.maturity_from} -> {e.maturity_to}\n"
            f"  source: {src}"
        )
    return "\n".join(lines)


def generate_digest(session: Session, kind: str) -> dict | None:
    events = _window_events(session, kind)
    if not events:
        return None
    # Keep the digest honest: only include events that pass selection rules,
    # plus everything if the window was quiet but had real events.
    important = [e for e in events if e.impact_level in ("High", "Critical")
                 or (e.maturity_from and e.maturity_to and e.maturity_from != e.maturity_to)]
    chosen = important or events[:5]

    input_payload = {"kind": kind, "events": [e.slug for e in chosen]}
    decision, _ = None, None
    # The digest prompt path is used when an LLM key is configured; otherwise a
    # deterministic digest is composed and still recorded for traceability.
    import asyncio

    async def _llm() -> DigestOutput | None:
        out, _ = await run_llm_stage(
            "digest", PROMPT_VERSIONS["digest"], input_payload,
            SYSTEM_GRAPHICS_ANALYST,
            DIGEST_PROMPT.format(kind=kind, events=_event_lines(chosen)),
            DigestOutput,
        )
        return DigestOutput.model_validate(out) if out else None

    try:
        decision = asyncio.run(_llm())
    except RuntimeError:
        decision = None

    date = datetime.now(timezone.utc).date()
    if decision is not None:
        title, body = decision.title, decision.body
        model_used = "llm"
    else:
        title = f"Graphics Engine Radar {kind} — {date.isoformat()}: {len(chosen)} 条值得关注的变化"
        parts = []
        for e in chosen:
            parts.append(
                f"### [{e.change_signal}] {e.title}\n\n"
                f"**发生了什么**: {e.change or e.summary}\n\n"
                f"**Why it matters**: {e.why_it_matters}\n\n"
                f"影响等级: {e.impact_level}"
                + (f" | 成熟度: {e.maturity_from} → {e.maturity_to}" if e.maturity_to else "")
            )
        body = "\n\n".join(parts)
        model_used = "heuristic-rules"

    record_ai_execution("digest", model_used, PROMPT_VERSIONS["digest"],
                        input_hash(input_payload), input_payload,
                        {"title": title, "events": [e.slug for e in chosen]},
                        success=True)

    existing = session.query(DailyDigest).filter_by(kind=kind).one_or_none()
    digest = existing or DailyDigest(kind=kind)
    if existing is None:
        session.add(digest)
    digest.date = datetime.now(timezone.utc)
    digest.title = title
    digest.body = body
    digest.event_ids = [str(e.id) for e in chosen]
    digest.generated_at = datetime.now(timezone.utc)
    session.commit()
    return {"kind": kind, "title": title, "events": len(chosen)}
