"""Versioned stage prompts (spec §18/§36).

Each stage has its own prompt and a version string recorded in AIExecution.
Stages must never be merged into one big summary prompt.
"""

PROMPT_VERSIONS = {
    "candidate_detection": "candidate-v1",
    "event_clustering": "cluster-v1",
    "technical_analysis": "tech-analysis-v1",
    "topic_mapping": "topic-v1",
    "impact_evaluation": "impact-v1",
    "digest": "digest-v1",
}

SYSTEM_GRAPHICS_ANALYST = """You are a senior real-time graphics engineer and technical intelligence analyst. \
You have shipped game engines and rendering backends across Vulkan, D3D12, Metal and WebGPU. \
You judge information like an engineer, not like a journalist: facts, capability changes, engineering impact. \
Never use marketing language. Never invent facts that are not supported by the provided evidence. \
Always answer with strict JSON only."""

CANDIDATE_DETECTION_PROMPT = """Decide whether the following item from source {source_type} of {object_name} \
describes a technical change worth deeper analysis for a graphics-engineering audience.

A candidate is something that introduces or announces: a new capability, platform/hardware support, \
API support, an architecture change, a specification/extension change, a significant performance change, \
a tooling capability, or adoption of a technology by an engine/vendor.

NOT a candidate: ordinary bugfixes, dependency bumps, CI changes, typos, docs-only edits, formatting, \
small refactors, routine crash fixes, job posts, marketing campaigns, game launches, art showcases, \
tutorials, duplicates.

Item title: {title}
Item content (truncated):
---
{content}
---

Answer with JSON only:
{{"candidate": true|false, "reason": "...", "signals": ["CAPABILITY"|"PLATFORM_SUPPORT"|"API_SUPPORT"|"ARCHITECTURE"|"SPECIFICATION"|"PERFORMANCE"|"QUALITY"|"TOOLING"|"ADOPTION"|"BREAKING_CHANGE"]}}"""

EVENT_CLUSTERING_PROMPT = """You are deciding whether a new candidate item belongs to an existing tracked event.

Existing event:
Title: {event_title}
Summary: {event_summary}
Objects: {event_objects}
Published: {event_published}

New item (source: {source_type}, object: {object_name}):
Title: {title}
Content (truncated):
---
{content}
---

Do both describe the same real-world technical change (e.g. one release reported by multiple sources)? \
Answer with JSON only:
{{"same_event": true|false, "confidence": 0.0-1.0, "reason": "..."}}"""

TECHNICAL_ANALYSIS_PROMPT = """Analyze this technical change for graphics engineers. Do NOT just summarize. \
Answer: did this capability exist before? What subsystem actually changed? Is this a real technical change \
or marketing repackaging? Which engines/APIs/GPUs/platforms are affected? Did a technology maturity stage \
transition occur (Research -> Prototype -> Open Source -> SDK -> Standard -> Engine Integration -> Production \
-> Cross-platform -> Mainstream)?

Object: {object_name} ({object_type})
Sources providing evidence:
{evidence}

Related known context (may be empty):
{related}

Answer with JSON only, using these exact keys:
{{"title": "...", "summary": "2-3 sentence factual summary", "what_changed": "...", "previous_state": "...", "new_state": "...",
"event_type": "VERSION_RELEASE|FEATURE_ADDED|CAPABILITY_ENABLED|ARCHITECTURE_CHANGE|SPEC_CHANGE|PERFORMANCE_CHANGE|QUALITY_CHANGE|TOOLCHAIN_CHANGE|TECHNOLOGY_ADOPTION|BREAKING_CHANGE",
"change_signal": "NEW|EXPAND|ADOPT|MATURE|SPEC|PERF|BREAK",
"objects": ["slug", ...], "platforms": [...], "technologies": [...],
"maturity_from": "Research|Prototype|Open Source|SDK|Standard|Engine Integration|Production|Cross-platform|Mainstream"|null,
"maturity_to": same|null,
"why_it_matters": "1-3 sentences of concrete engineering judgment: what an engine/graphics engineer can now do or should watch out for, and why. No marketing language.",
"who_should_care": "...", "evidence_quality": "high|medium|low", "confidence": 0.0-1.0}}"""

TOPIC_MAPPING_PROMPT = """Assign topics to this graphics-technology event.

Available topics (slug: description):
{topic_list}

Event:
Title: {title}
Summary: {summary}
What changed: {what_changed}

Answer with JSON only:
{{"topics": [{{"slug": "...", "relation": "direct|affected|enabled|adopted|related", "confidence": 0.0-1.0}}]}}
Pick 1-5 topics. Use "direct" for what the event is about."""

IMPACT_EVALUATION_PROMPT = """Score the engineering impact of this graphics-technology event on five 0-5 dimensions:
- capability: does it create or unlock a new technical capability?
- engineering: how much does it change engineering work (code, pipeline, architecture)?
- adoption: does it signal adoption (vendor support, engine integration, standardization)?
- scope: how wide is the affected surface (platforms, engines, teams)?
- evidence: how reliable and complete is the evidence?

Then map to an impact level. Rules that MUST raise the level: a maturity transition occurred \
(maturity_from != maturity_to), a cross-platform expansion, a major architecture change, a major standard \
change, or a breaking change -> at least "High". Use "Critical" only for events that immediately change \
what most graphics engineers can build (e.g. a major API revision, a new platform-wide capability).

Event:
Title: {title}
What changed: {what_changed}
Event type: {event_type} / Signal: {change_signal}
Maturity: {maturity_from} -> {maturity_to}
Evidence quality: {evidence_quality}

Answer with JSON only:
{{"capability": 0-5, "engineering": 0-5, "adoption": 0-5, "scope": 0-5, "evidence": 0-5, "impact_level": "Critical|High|Notable", "reason": "..."}}"""

DIGEST_PROMPT = """Write a {kind} digest for graphics engineers covering the events below. \
Focus on what actually changed technically and any maturity/phase transitions. Do not pad; \
if only a few events matter, the digest is short. Never concatenate per-day summaries; analyze the window.

Events:
{events}

Answer with JSON only:
{{"title": "...", "body": "markdown, 150-400 words for daily, longer for weekly/monthly"}}"""
