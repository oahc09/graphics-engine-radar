"""Embeddings for event retrieval (spec §22/§11).

Provider selection:
- If LLM_API_KEY is set: OpenAI-compatible embedding API (dim must match
  LLM_EMBEDDING_DIM; reindex events after changing providers).
- Otherwise: deterministic feature-hashing embedder over normalized token
  n-grams. Same storage dimension, cosine-comparable, no network dependency.

pgvector columns: events.title_embedding / events.change_embedding.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

import httpx

from radar_domain.settings import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.\-]*")

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "be", "this", "that", "it", "as", "at", "by", "from",
    "new", "add", "added", "support", "update", "updated", "release", "version",
}


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in STOPWORDS]


class HashingEmbedder:
    """Feature hashing: unigrams+bigrams -> signed fixed-dim vector, L2 normed."""

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def _bucket(self, gram: str) -> tuple[int, float]:
        h = int.from_bytes(hashlib.md5(gram.encode("utf-8")).digest()[:8], "little")
        idx = h % self.dim
        sign = 1.0 if (h >> 63) & 1 else -1.0
        return idx, sign

    def embed(self, text: str) -> list[float]:
        toks = _tokens(text)
        grams = list(toks) + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        vec = [0.0] * self.dim
        counts = Counter(grams)
        for gram, count in counts.items():
            idx, sign = self._bucket(gram)
            vec[idx] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class APIEmbedder:
    def __init__(self, model: str, dim: int) -> None:
        self.model = model
        self.dim = dim

    async def embed(self, text: str) -> list[float]:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.llm_api_base.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": self.model, "input": text[:8000]},
            )
            resp.raise_for_status()
            vec = resp.json()["data"][0]["embedding"]
        return _fit_dim(vec, self.dim)


def _fit_dim(vec: list[float], dim: int) -> list[float]:
    if len(vec) == dim:
        return vec
    if len(vec) > dim:
        factor = len(vec) / dim
        out = []
        for i in range(dim):
            lo, hi = int(i * factor), max(int((i + 1) * factor), int(i * factor) + 1)
            out.append(sum(vec[lo:hi]) / (hi - lo))
        return out
    return vec + [0.0] * (dim - len(vec))


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


_embedder: HashingEmbedder | None = None


def get_embedder() -> HashingEmbedder:
    """Synchronous embedder used by the pipeline. The API embedder is exposed
    for environments with an embedding key; the hashing embedder guarantees the
    pipeline runs with zero external dependencies."""
    global _embedder
    if _embedder is None:
        _embedder = HashingEmbedder(get_settings().llm_embedding_dim)
    return _embedder


def embed_sync(text: str) -> list[float]:
    return get_embedder().embed(text)
