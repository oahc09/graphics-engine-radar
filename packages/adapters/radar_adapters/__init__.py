from radar_adapters.base import FetchResult, RawItemDraft, SourceAdapter, get_adapter, known_adapters, register
from radar_adapters.github import GitHubIssueAdapter, GitHubPRAdapter, GitHubReleaseAdapter
from radar_adapters.http_sources import (
    HTMLAdapter,
    RSSAdapter,
    ReleaseNotesAdapter,
    SpecRegistryAdapter,
)
from radar_adapters.normalize import canonical_url, content_hash

__all__ = [
    "FetchResult",
    "RawItemDraft",
    "SourceAdapter",
    "get_adapter",
    "known_adapters",
    "register",
    "GitHubReleaseAdapter",
    "GitHubPRAdapter",
    "GitHubIssueAdapter",
    "RSSAdapter",
    "HTMLAdapter",
    "ReleaseNotesAdapter",
    "SpecRegistryAdapter",
    "canonical_url",
    "content_hash",
]
