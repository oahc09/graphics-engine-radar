"""Candidate Detection (spec §21 / M6): rules → lightweight classification →
strong model. First pass costs nothing; LLM only when configured."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from radar_intelligence.llm import run_fallback, run_llm_stage
from radar_intelligence.rule_filter import _SIGNAL_PATTERNS
from radar_prompts import (
    CANDIDATE_DETECTION_PROMPT,
    PROMPT_VERSIONS,
    SYSTEM_GRAPHICS_ANALYST,
)

VERSION_RELEASE_RE = re.compile(
    r"\b(v?\d+\.\d+(\.\d+)?)\b|\brelease\b|\btag\b|\balpha\b|\bbeta\b|\brc\b|\bbranch\b|\bshipping\b|\bshipped\b", re.I)

# Graphics-domain relevance gate: blog/community/platform feeds publish plenty
# of non-graphics content (general Android APIs, etc.). Monitored objects that
# are not dedicated graphics repos must still pass this gate to become
# candidates — monitoring scope does not waive topical relevance (spec §2.2).
GRAPHICS_RELEVANCE_RE = re.compile(
    r"render|gpu|shader|graphi|vulkan|opengl|webgpu|webgl|metal\b|directx|d3d|dx12|"
    r"frame ?rate|frame ?time|raster|mesh|texture|geometry|\b3d\b|three\.?js|splat|"
    r"ray ?trac|engine|composit|canvas|skia|impeller|display|draw call|nanite|"
    r"lod\b|pipeline|gfx|graphics", re.I)


class CandidateDecision(BaseModel):
    candidate: bool
    reason: str = ""
    signals: list[str] = Field(default_factory=list)


SIGNAL_WEIGHTS = {
    "spec_change": 3, "new_backend": 3, "capability": 2, "platform": 1,
    "ray_tracing": 2, "gpu_driven": 2, "neural": 2, "performance": 1,
    "breaking": 3, "webgpu": 2, "version_release": 1,
}


def heuristic_candidate(item_title: str, item_content: str, object_name: str,
                        source_type: str) -> CandidateDecision:
    text = f"{item_title}\n{item_content}".lower()[:8000]
    signals: list[str] = []
    score = 0
    for sid, pat in _SIGNAL_PATTERNS:
        if pat.search(text):
            signals.append(sid)
            score += SIGNAL_WEIGHTS.get(sid, 1)
    if VERSION_RELEASE_RE.search(item_title):
        score += 1
    # Releases from monitored objects are structural events by definition.
    if source_type in ("github_release", "release_notes", "spec_registry"):
        score += 2
    # Relevance gate for feed-like sources (spec §2.2): object popularity does
    # not make non-graphics content a candidate.
    if source_type in ("rss", "official_blog", "community", "html", "documentation"):
        if not GRAPHICS_RELEVANCE_RE.search(text):
            return CandidateDecision(
                candidate=False,
                reason="heuristic: no graphics-domain relevance in feed item")
    candidate = score >= 4 and bool(signals)
    if candidate:
        return CandidateDecision(candidate=True, reason=f"heuristic signals: {', '.join(signals)}")
    return CandidateDecision(candidate=False,
                             reason=f"heuristic score {score} below threshold; signals: {signals or ['none']}")


async def detect_candidate(raw, object_, source) -> CandidateDecision:
    """Two-tier: heuristic first; LLM when configured (spec §21)."""
    title = raw.title or ""
    content = (raw.content or "")[:4000]
    input_payload = {"raw_item_id": str(raw.id), "title": title, "object": object_.slug,
                     "source_type": source.type}

    decision, model = await run_llm_stage(
        "candidate_detection", PROMPT_VERSIONS["candidate_detection"], input_payload,
        SYSTEM_GRAPHICS_ANALYST,
        CANDIDATE_DETECTION_PROMPT.format(
            source_type=source.type, object_name=object_.name,
            title=title, content=content),
        CandidateDecision,
    )
    if decision is not None:
        return CandidateDecision.model_validate(decision)

    heuristic = heuristic_candidate(title, content, object_.name, source.type)
    run_fallback("candidate_detection", PROMPT_VERSIONS["candidate_detection"],
                 input_payload, heuristic.model_dump())
    return heuristic
