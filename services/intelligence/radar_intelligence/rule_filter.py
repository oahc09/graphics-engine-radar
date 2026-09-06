"""Rule Filter (spec §13 / M5): the cheap first layer.

Default noise is marked `ignored` with a reason — never deleted — so future
algorithm upgrades can re-analyze (spec §13). Everything else stays `new`.
"""

from __future__ import annotations

import re

from radar_domain.enums import RawFilterStatus
from radar_domain.models import RawItem

# (rule_id, compiled pattern) — matched against "title\ncontent" lowercased.
_NOISE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("dependency_bump", re.compile(
        r"\b(bump|update|upgrade)\b[^\n]{0,40}\b(dependenc|from [\d.]+ to [\d.]+|v?\d+\.\d+(\.\d+)?)\b"
        r"|\bbump \S+ from [\d.]+ to [\d.]+")),
    ("ci_only", re.compile(
        r"\b(ci|continuous integration|github actions|circleci|buildkite)\b[^\n]{0,30}\b"
        r"(workflow|pipeline|build|runner|failure|fix ci|ci fix)\b"
        r"|^\s*fix(ing)? ci\b|\btrigger ci\b")),
    ("typo_docs", re.compile(
        r"\b(typo|typo fix|fix typo|docs?:?\s|documentation:?\s|docstring)\b"
        r"|\b(readme|changelog formatting|spelling|grammar)\b")),
    ("formatting_refactor", re.compile(
        r"^\s*(style|format|clang-format|prettier|black|lint)[:\s]"
        r"|\b(code ?style|reformat|formatting only|cosmetic)\b"
        r"|\b(minor refactor|internal refactor|refactor only)\b")),
    ("ordinary_bugfix", re.compile(
        r"^\s*fix(ed|es)?[:\s].{0,80}$"
        r"|\b(crash fix|null ?check|off-?by-?one|memory leak in [a-z ]{0,20}$)")),
    ("flaky_test", re.compile(r"\b(flaky|failing test|test timeout|fix test)\b")),
    ("hiring", re.compile(r"\b(hiring|we'?re hiring|job opening|careers?|position open)\b")),
    ("marketing_event", re.compile(
        r"\b(webinar|summit|conference (sponsor|booth)|black friday|sale\b|discount\b|"
        r"giveaway|sponsor(ed|ship)\b)")),
    ("game_launch", re.compile(r"\b(game launch|now available on steam|launch trailer|release trailer)\b")),
    ("art_showcase", re.compile(r"\b(showcase|art dump|render gallery|fan art|made with)\b")),
    ("tutorial", re.compile(r"\b(tutorial|course|how to build|getting started guide|beginner guide)\b")),
]

# Strong upgrade signals that override a weak noise match.
_SIGNAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("spec_change", re.compile(r"\b(spec(ification)?|extension|registry|profile|revision|ratif|khr_|vk_|vkspec)\b")),
    ("new_backend", re.compile(r"\b(new (backend|renderer)|adds? (a )?(webgpu|vulkan|metal|dx12|d3d12|opengl) (backend|support|renderer))\b")),
    ("version_release", re.compile(r"\b(v?\d+\.\d+ (\(|released|is out)|release (notes|announcement)|major release|milestone)\b")),
    ("capability", re.compile(r"\b(adds? support|new feature|now supports|enables?|experimental support|initial support|implementation of)\b")),
    ("platform", re.compile(r"\b(android|ios|macos|linux|windows|web|wasm|visionos|switch|playstation|xbox|mobile)\b")),
    ("ray_tracing", re.compile(r"\b(ray ?trac|rtx|path trac)\b")),
    ("gpu_driven", re.compile(r"\b(gpu driven|mesh shader|bindless|work graph|virtual geometry|nanite)\b")),
    ("neural", re.compile(r"\b(neural|machine learning|ml |ai-generated|gaussian splat|nerf|dlss|frame generation)\b")),
    ("performance", re.compile(r"\b(\d+x (faster|speedup)|performance improvement|reduc(es?|ed) (cpu|gpu|memory|draw ?calls?)|optimiz)\b")),
    ("breaking", re.compile(r"\b(breaking change|api break|removed api|deprecated)\b")),
    ("webgpu", re.compile(r"\b(webgpu|wgsl|dawn|wgpu)\b")),
]


def classify_noise(raw: RawItem) -> tuple[bool, str | None]:
    text = f"{raw.title}\n{raw.content}".lower()[:8000]
    if not text.strip():
        return True, "empty_content"

    noise_hits = [(rid, pat.search(text)) for rid, pat in _NOISE_PATTERNS]
    noise_hits = [(rid, m) for rid, m in noise_hits if m]
    if not noise_hits:
        return False, None

    signal_hits = [sid for sid, pat in _SIGNAL_PATTERNS if pat.search(text)]
    rid = noise_hits[0][0]
    # CI/infra items mentioning a platform name (e.g. "macOS runner") must not
    # be rescued by the weak platform signal alone.
    if rid in ("ci_only", "flaky_test"):
        signal_hits = [s for s in signal_hits if s != "platform"]
    if signal_hits:
        # Noise rule matched, but the item also carries a strong technical
        # signal. Keep it for candidate detection; annotate the tension.
        return False, None
    return True, f"noise:{rid}"


def apply_rule_filter(session, limit: int | None = None) -> dict:
    """Run the rule filter over `new` RawItems. Returns counters."""
    q = session.query(RawItem).filter(RawItem.filter_status == RawFilterStatus.NEW.value)
    if limit:
        q = q.limit(limit)
    items = q.all()
    ignored = 0
    for item in items:
        is_noise, reason = classify_noise(item)
        if is_noise:
            item.filter_status = RawFilterStatus.IGNORED.value
            item.filter_reason = reason
            ignored += 1
    session.commit()
    return {"scanned": len(items), "ignored": ignored,
            "kept": len(items) - ignored}
