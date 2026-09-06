from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String enum whose values serialize as plain strings."""


class ObjectType(StrEnum):
    GAME_ENGINE = "game_engine"
    RENDERING_ENGINE = "rendering_engine"
    WEB_ENGINE = "web_engine"
    GRAPHICS_RUNTIME = "graphics_runtime"
    GRAPHICS_API = "graphics_api"
    GPU_VENDOR = "gpu_vendor"
    PLATFORM = "platform"
    DCC = "dcc"
    TOOL = "tool"
    STANDARD = "standard"
    TECHNOLOGY = "technology"


class SourceType(StrEnum):
    GITHUB_RELEASE = "github_release"
    GITHUB_PR = "github_pr"
    GITHUB_ISSUE = "github_issue"
    GITHUB_DISCUSSION = "github_discussion"
    RSS = "rss"
    RELEASE_NOTES = "release_notes"
    OFFICIAL_BLOG = "official_blog"
    SPEC_REGISTRY = "spec_registry"
    DOCUMENTATION = "documentation"
    ROADMAP = "roadmap"
    CONFERENCE = "conference"
    COMMUNITY = "community"
    HTML = "html"


class RawFilterStatus(StrEnum):
    NEW = "new"
    IGNORED = "ignored"
    CANDIDATE = "candidate"
    PROCESSED = "processed"


class EventType(StrEnum):
    VERSION_RELEASE = "VERSION_RELEASE"
    FEATURE_ADDED = "FEATURE_ADDED"
    CAPABILITY_ENABLED = "CAPABILITY_ENABLED"
    ARCHITECTURE_CHANGE = "ARCHITECTURE_CHANGE"
    SPEC_CHANGE = "SPEC_CHANGE"
    PERFORMANCE_CHANGE = "PERFORMANCE_CHANGE"
    QUALITY_CHANGE = "QUALITY_CHANGE"
    TOOLCHAIN_CHANGE = "TOOLCHAIN_CHANGE"
    TECHNOLOGY_ADOPTION = "TECHNOLOGY_ADOPTION"
    BREAKING_CHANGE = "BREAKING_CHANGE"


class ChangeSignal(StrEnum):
    NEW = "NEW"
    EXPAND = "EXPAND"
    ADOPT = "ADOPT"
    MATURE = "MATURE"
    SPEC = "SPEC"
    PERF = "PERF"
    BREAK = "BREAK"


class EventStatus(StrEnum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    PUBLISHED = "published"
    REJECTED = "rejected"
    MERGED = "merged"


class EventSourceRole(StrEnum):
    PRIMARY = "primary"
    OFFICIAL = "official"
    SUPPORTING = "supporting"
    COMMUNITY = "community"
    DISCOVERY = "discovery"


class EventTopicRelation(StrEnum):
    DIRECT = "direct"
    AFFECTED = "affected"
    ENABLED = "enabled"
    ADOPTED = "adopted"
    RELATED = "related"


class ImpactLevel(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    NOTABLE = "Notable"


class MaturityStage(StrEnum):
    RESEARCH = "Research"
    PROTOTYPE = "Prototype"
    OPEN_SOURCE = "Open Source"
    SDK = "SDK"
    STANDARD = "Standard"
    ENGINE_INTEGRATION = "Engine Integration"
    PRODUCTION = "Production"
    CROSS_PLATFORM = "Cross-platform"
    MAINSTREAM = "Mainstream"


class TrendState(StrEnum):
    ACCELERATING = "Accelerating"
    GROWING = "Growing"
    STABLE = "Stable"
    COOLING = "Cooling"
    RESEARCH_HEAVY = "Research-heavy"


class Domain(StrEnum):
    ENGINE = "engine"
    GRAPHICS_API = "graphics_api"
    GPU_PLATFORM = "gpu_platform"
    RENDERING_TECH = "rendering_tech"
    TOOLING = "tooling"
    CONTENT_PIPELINE = "content_pipeline"
    STANDARD = "standard"
