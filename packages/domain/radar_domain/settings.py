from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://radar:radar@localhost:5433/radar"

    # LLM provider. One of:
    #   openai     — any OpenAI-compatible HTTP API (OpenAI/DeepSeek/Qwen/GLM/
    #                OpenRouter/Moonshot/Ollama/... incl. Claude via OpenRouter
    #                or Anthropic's OpenAI-compat endpoint). Needs LLM_API_KEY.
    #   claude-cli — shell out to the local `claude` CLI (Claude Code, -p mode).
    #                Uses your Claude subscription; no API key needed.
    #   codex-cli  — shell out to the local `codex` CLI (codex exec).
    #                Uses your ChatGPT account; no API key needed.
    llm_provider: str = "openai"
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""  # empty = provider default
    llm_cli_timeout: float = 240.0
    # comma-separated stage list allowed to call the LLM, e.g.
    # "candidate_detection,technical_analysis,impact_evaluation". Empty = all.
    llm_stages: str = ""
    llm_embedding_model: str = "text-embedding-3-small"
    llm_embedding_dim: int = 256  # storage dim for pgvector columns

    github_token: str = ""

    http_timeout_seconds: float = 30.0
    collector_max_items_per_fetch: int = 50

    config_dir: Path = REPO_ROOT / "config"
    api_port: int = 8300
    web_port: int = 8301
    # embedded database data dir (scripts/embedded_db.py also honors the
    # GRADAR_DATA_DIR environment variable directly)
    data_dir: Path = REPO_ROOT / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
