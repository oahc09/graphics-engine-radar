"""Technical Analysis (spec §24/§14 / M8) + Topic Mapping + Maturity + Impact
(spec §15/§16/§17 / M9).

The heuristic analyzer is deterministic and template-driven; when an LLM key
is configured the staged prompts in radar_prompts run instead. Every stage
decision is recorded in AIExecution (spec §36).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from radar_intelligence.embeddings import embed_sync
from radar_intelligence.llm import input_hash, record_ai_execution, run_llm_stage
from radar_prompts import (
    IMPACT_EVALUATION_PROMPT,
    PROMPT_VERSIONS,
    SYSTEM_GRAPHICS_ANALYST,
    TECHNICAL_ANALYSIS_PROMPT,
    TOPIC_MAPPING_PROMPT,
)

MATURITY_ORDER = [
    "Research", "Prototype", "Open Source", "SDK", "Standard",
    "Engine Integration", "Production", "Cross-platform", "Mainstream",
]

_BACKEND_RE = re.compile(
    r"\b(webgpu|vulkan|metal|d3d12|direct3d 12|directx 12|opengl|opengl es)\b", re.I)
_PLATFORM_RE = re.compile(
    r"\b(android|ios|macos|windows|linux|web|wasm|visionos|browser|mobile|desktop|switch|playstation|xbox)\b", re.I)
_EXPERIMENTAL_RE = re.compile(r"\b(experimental|preview|alpha|initial support|prototype|wip|proof of concept)\b", re.I)
_BETA_RE = re.compile(r"\b(beta|release candidate|rc\d?)\b", re.I)
# Deliberately strict: bare "stable"/"1.0" appear in countless release notes
# and would fabricate maturity transitions (spec §16 requires real ones).
_STABLE_RE = re.compile(
    r"\b(production.?ready|now stable|is stable|out of beta|graduat|generally available|"
    r"declared stable|promoted to stable|reaches stable|first stable)\b", re.I)
_BREAKING_RE = re.compile(r"\b(breaking change|api break|backwards.?incompatible|removed (api|support)|deprecat)\b", re.I)
_PERF_RE = re.compile(r"\b(\d+(\.\d+)?x (faster|speedup|performance)|\d+%\s*(faster|faster|improvement|reduction)|performance improvement|reduced (cpu|gpu|memory|draw ?calls?)|optimization)s?\b", re.I)
_SPEC_RE = re.compile(r"\b(specification|registry|extension|khr|profile|ratif|revision|standard|w3c)\b", re.I)
_ADOPT_RE = re.compile(r"\b(adopt|integrat|switch(ed|ing)? to|migrat|ships with|uses)\b", re.I)


class TechnicalAnalysis(BaseModel):
    title: str
    summary: str = ""
    what_changed: str = ""
    previous_state: str = ""
    new_state: str = ""
    event_type: str = "FEATURE_ADDED"
    change_signal: str = "NEW"
    objects: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    maturity_from: str | None = None
    maturity_to: str | None = None
    why_it_matters: str = ""
    who_should_care: str = ""
    evidence_quality: str = "medium"
    confidence: float = 0.5


EVENT_TYPE_RULES = [
    ("BREAKING_CHANGE", _BREAKING_RE),
    ("SPEC_CHANGE", _SPEC_RE),
    ("PERFORMANCE_CHANGE", _PERF_RE),
]


def _detect_platforms(text: str) -> list[str]:
    found = {m.group(1).lower() for m in _PLATFORM_RE.finditer(text)}
    return sorted(found)[:6]


def _detect_maturity_transition(headline: str) -> tuple[str | None, str | None]:
    """Only claim a transition when the *headline* states it explicitly.
    Bodies of release notes mention alpha/beta of sub-features constantly;
    treating that as a project-level maturity change fabricated transitions."""
    if _STABLE_RE.search(headline):
        if _BETA_RE.search(headline) or _EXPERIMENTAL_RE.search(headline):
            return "Prototype", "Production"
        return "SDK", "Production"
    if _BETA_RE.search(headline) and _ADOPT_RE.search(headline):
        return "Prototype", "SDK"
    return None, None


def heuristic_analysis(object_, raw_items: list, related_titles: list[str]) -> TechnicalAnalysis:
    """Deterministic staged analysis without an LLM.

    Composes concrete, engineering-oriented judgments from detected signals;
    never emits generic marketing phrases.
    """
    text = "\n".join((r.title or "") + "\n" + (r.content or "")[:3000]
                     for r in raw_items)[:12000]
    text_l = text.lower()
    title = raw_items[0].title or "(untitled)"
    # Signals are judged on the headline (title + first chars of body), not the
    # full 12k body: release notes mention unrelated platforms/sub-features and
    # that produced false signals.
    headline = f"{title}\n{(raw_items[0].content or '')[:600]}".lower()
    platforms = _detect_platforms(headline)
    backends = {m.group(1).upper() for m in _BACKEND_RE.finditer(headline)}
    backends = {b if b != "DIRECT3D 12" and b != "DIRECTX 12" and b != "D3D12" else "D3D12" for b in backends}

    event_type = "FEATURE_ADDED"
    change_signal = "NEW"
    if raw_items[0].source.type == "github_release" or VERSION_TAG_RE.search(title):
        event_type = "VERSION_RELEASE"
    # classify strictly by title (release-note bodies mention unrelated
    # extensions/sub-features and that mislabeled tool releases as SPEC_CHANGE)
    for et, pat in EVENT_TYPE_RULES:
        if pat.search(title.lower()):
            event_type = et
            break
    if event_type == "SPEC_CHANGE":
        change_signal = "SPEC"
    elif event_type == "BREAKING_CHANGE":
        change_signal = "BREAK"
    elif event_type == "PERFORMANCE_CHANGE":
        change_signal = "PERF"
    elif _ADOPT_RE.search(headline):
        change_signal = "ADOPT"
        event_type = "TECHNOLOGY_ADOPTION" if event_type == "FEATURE_ADDED" else event_type

    maturity_from, maturity_to = _detect_maturity_transition(headline)
    if maturity_from:
        change_signal = "MATURE" if change_signal not in ("BREAK", "SPEC") else change_signal

    object_name = object_.name
    plat_str = "、".join(p.capitalize() for p in platforms) if platforms else "相关平台"

    what_changed = f"{object_name}: {title.strip()[:160]}"
    previous_state = "该能力此前不存在于该对象" if change_signal == "NEW" else "该对象已有相关能力,本次为变化更新"
    new_state = f"{object_name} 当前状态: {title.strip()[:120]}"

    # --- why_it_matters: concrete engineering judgment templates ---
    reasons: list[str] = []
    if ("backend" in headline and backends) or re.search(r"new (backend|renderer)", headline):
        reasons.append(
            f"{object_name} 为 {('、'.join(sorted(backends)))} 引入/扩展了后端支持, "
            "意味着基于该渲染路径的引擎可以减少自行维护平台 fallback backend 的成本。")
    if _SPEC_RE.search(headline):
        reasons.append(
            "这是规范/扩展层面的变化,影响所有计划跟进实现的驱动与引擎团队; "
            "跟进节奏决定了后续跨硬件一致性的验证成本。")
    if platforms and any(p in platforms for p in ("mobile", "android", "ios")):
        reasons.append(
            f"变化覆盖移动平台({plat_str}), 属于 Desktop → Mobile 方向的扩展信号; "
            "面向移动端交付的团队需要评估该能力在目标 GPU 上的可用性。")
    if maturity_to:
        reasons.append(
            f"技术成熟度从 {maturity_from} 迁移到 {maturity_to}: "
            "这意味着该技术开始从试验阶段进入可评估/可生产的阶段, "
            "是决定是否投入工程资源进行集成的关键节点。")
    if _PERF_RE.search(headline):
        reasons.append("带量化性能变化, 直接影响帧预算与渲染管线取舍, 需要在目标硬件上复测而非直接采信。")
    if _BREAKING_RE.search(headline):
        reasons.append("包含破坏性变更, 已有集成代码需要在升级时做迁移评估。")
    if not reasons:
        reasons.append(
            f"该变化改变了 {object_name} 的技术能力面, 对基于它构建渲染/引擎功能的团队有直接的工程参考价值。")
    why_it_matters = " ".join(reasons[:3])

    who_should_care = (
        f"使用 {object_name} 的引擎/渲染工程师, 以及关注 {plat_str} 图形能力的技术选型者。")

    evidence_quality = "high" if len(raw_items) >= 2 else "medium"
    confidence = min(0.9, 0.5 + 0.1 * len(raw_items))

    return TechnicalAnalysis(
        title=title.strip()[:200],
        summary=(f"{object_name} 在 {plat_str} 上的技术变化: {title.strip()[:150]}"),
        what_changed=what_changed,
        previous_state=previous_state,
        new_state=new_state,
        event_type=event_type,
        change_signal=change_signal,
        objects=[object_.slug],
        platforms=platforms,
        technologies=sorted(backends) if backends else [],
        maturity_from=maturity_from,
        maturity_to=maturity_to,
        why_it_matters=why_it_matters,
        who_should_care=who_should_care,
        evidence_quality=evidence_quality,
        confidence=round(confidence, 2),
    )


VERSION_TAG_RE = re.compile(r"\bv?\d+\.\d+")


async def analyze_technical(object_, raw_items: list, related_titles: list[str]) -> TechnicalAnalysis:
    """Staged strong-model analysis; heuristic fallback keeps the pipeline real."""
    input_payload = {
        "object": object_.slug,
        "evidence": [{"title": r.title, "url": r.url, "source_type": r.source.type}
                     for r in raw_items],
        "related": related_titles,
    }
    evidence_text = "\n".join(
        f"- [{r.source.type}] {r.title}\n  url: {r.url}\n  content: {(r.content or '')[:2500]}"
        for r in raw_items)
    decision, _ = await run_llm_stage(
        "technical_analysis", PROMPT_VERSIONS["technical_analysis"], input_payload,
        SYSTEM_GRAPHICS_ANALYST,
        TECHNICAL_ANALYSIS_PROMPT.format(
            object_name=object_.name, object_type=object_.type,
            evidence=evidence_text, related="\n".join(related_titles) or "(none)"),
        TechnicalAnalysis,
    )
    if decision is not None:
        return TechnicalAnalysis.model_validate(decision)
    heuristic = heuristic_analysis(object_, raw_items, related_titles)
    record_ai_execution("technical_analysis", "heuristic-rules",
                        PROMPT_VERSIONS["technical_analysis"],
                        input_hash(input_payload), input_payload,
                        heuristic.model_dump(), success=True)
    return heuristic


class TopicAssignment(BaseModel):
    slug: str
    relation: str = "direct"
    confidence: float = 0.5


class TopicMapping(BaseModel):
    topics: list[TopicAssignment]


def heuristic_topic_mapping(title: str, what_changed: str, topics: list) -> TopicMapping:
    text = f"{title} {what_changed}".lower()
    assigned: list[TopicAssignment] = []
    for topic in topics:
        kws = list(topic.keywords or []) + [topic.name.lower()]
        hits = [k for k in kws if k and k.lower() in text]
        if not hits:
            continue
        direct = any(h in (title or "").lower() for h in hits)
        assigned.append(TopicAssignment(
            slug=topic.slug,
            relation="direct" if direct else "related",
            confidence=0.8 if direct else 0.5,
        ))
    assigned.sort(key=lambda a: a.confidence, reverse=True)
    return TopicMapping(topics=assigned[:5])


async def map_topics(title: str, summary: str, what_changed: str, topic_rows: list) -> TopicMapping:
    mapping = heuristic_topic_mapping(title, f"{summary} {what_changed}", topic_rows)
    topic_list = "\n".join(f"- {t.slug}: {t.name}" for t in topic_rows)
    input_payload = {"title": title, "summary": summary, "what_changed": what_changed}
    decision, _ = await run_llm_stage(
        "topic_mapping", PROMPT_VERSIONS["topic_mapping"], input_payload,
        SYSTEM_GRAPHICS_ANALYST,
        TOPIC_MAPPING_PROMPT.format(topic_list=topic_list, title=title,
                                    summary=summary, what_changed=what_changed),
        TopicMapping,
    )
    if decision is not None:
        return TopicMapping.model_validate(decision)
    return mapping


class ImpactScores(BaseModel):
    capability: int = Field(ge=0, le=5, default=0)
    engineering: int = Field(ge=0, le=5, default=0)
    adoption: int = Field(ge=0, le=5, default=0)
    scope: int = Field(ge=0, le=5, default=0)
    evidence: int = Field(ge=0, le=5, default=0)
    impact_level: str = "Notable"
    reason: str = ""


def heuristic_impact(analysis: TechnicalAnalysis) -> ImpactScores:
    scores = ImpactScores()
    et, signal = analysis.event_type, analysis.change_signal
    scores.capability = 4 if et in ("FEATURE_ADDED", "CAPABILITY_ENABLED", "ARCHITECTURE_CHANGE") else 3
    scores.capability = 2 if et == "QUALITY_CHANGE" else scores.capability
    scores.engineering = 4 if et in ("ARCHITECTURE_CHANGE", "BREAKING_CHANGE", "TOOLCHAIN_CHANGE") else 3
    scores.adoption = 4 if signal in ("ADOPT", "MATURE") or analysis.maturity_to else 2
    scores.scope = 4 if len(analysis.platforms) >= 2 else (3 if analysis.platforms else 2)
    scores.evidence = 5 if analysis.evidence_quality == "high" else (3 if analysis.evidence_quality == "medium" else 1)

    level = "Notable"
    maturity_transition = bool(analysis.maturity_from and analysis.maturity_to
                               and analysis.maturity_from != analysis.maturity_to)
    cross_platform = len(analysis.platforms) >= 2
    major_arch = et in ("ARCHITECTURE_CHANGE",)
    major_standard = et == "SPEC_CHANGE"
    breaking = et == "BREAKING_CHANGE"
    if (maturity_transition or major_arch or major_standard or breaking
            or (cross_platform and scores.capability >= 4)):
        level = "High"
    if (maturity_transition and (major_standard or major_arch) and cross_platform
            and et != "VERSION_RELEASE"):
        level = "Critical"
    scores.impact_level = level
    scores.reason = (
        f"event_type={et}, signal={signal}, maturity={analysis.maturity_from}->{analysis.maturity_to}, "
        f"platforms={analysis.platforms}")
    return scores


async def evaluate_impact(analysis: TechnicalAnalysis) -> ImpactScores:
    input_payload = {
        "title": analysis.title, "what_changed": analysis.what_changed,
        "event_type": analysis.event_type, "change_signal": analysis.change_signal,
        "maturity_from": analysis.maturity_from, "maturity_to": analysis.maturity_to,
        "evidence_quality": analysis.evidence_quality,
    }
    decision, _ = await run_llm_stage(
        "impact_evaluation", PROMPT_VERSIONS["impact_evaluation"], input_payload,
        SYSTEM_GRAPHICS_ANALYST,
        IMPACT_EVALUATION_PROMPT.format(
            title=analysis.title, what_changed=analysis.what_changed,
            event_type=analysis.event_type, change_signal=analysis.change_signal,
            maturity_from=analysis.maturity_from or "n/a",
            maturity_to=analysis.maturity_to or "n/a",
            evidence_quality=analysis.evidence_quality),
        ImpactScores,
    )
    if decision is not None:
        return ImpactScores.model_validate(decision)
    heuristic = heuristic_impact(analysis)
    record_ai_execution("impact_evaluation", "heuristic-rules",
                        PROMPT_VERSIONS["impact_evaluation"],
                        input_hash(input_payload), input_payload,
                        heuristic.model_dump(), success=True)
    return heuristic


def embed_event(title: str, change: str) -> tuple[list, list]:
    return embed_sync(title), embed_sync(change)
