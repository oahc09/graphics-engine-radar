from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "ref_src", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid",
    "cmpid", "spm", "share", "source",
}


def canonical_url(url: str | None) -> str | None:
    """Canonicalize a URL so query-string/tracking differences do not create
    duplicate RawItems (spec §35)."""
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url
    scheme = parts.scheme.lower() or "https"
    host = (parts.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in TRACKING_PARAMS]
    query_str = urlencode(query)
    return urlunsplit((scheme, host, path, query_str, ""))


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
