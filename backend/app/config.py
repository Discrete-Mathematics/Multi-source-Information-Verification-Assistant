"""Runtime configuration, read from environment with sane defaults.

The whole app is driven by three Anthropic env vars that Claude Code already
sets in this environment (ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL /
ANTHROPIC_MODEL).  Evidence sources are all key-free, so there is nothing else
to configure to get a running demo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass
class Settings:
    # --- LLM ---
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    anthropic_base_url: str = field(
        default_factory=lambda: _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    )
    # Model used for the heavy reasoning steps (extraction, report).
    model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-opus-4-8"))
    # Cheaper model for high-volume steps (stance classification).  Falls back
    # to the main model if the env var is unset — keeps the demo robust on
    # proxies that only expose one model.
    fast_model: str = field(
        default_factory=lambda: _env("FACTCHECK_FAST_MODEL") or _env("ANTHROPIC_MODEL", "claude-opus-4-8")
    )

    # --- pipeline knobs ---
    max_claims: int = int(_env("FACTCHECK_MAX_CLAIMS", "8") or 8)
    queries_per_claim: int = int(_env("FACTCHECK_QUERIES_PER_CLAIM", "3") or 3)
    evidence_per_query: int = int(_env("FACTCHECK_EVIDENCE_PER_QUERY", "4") or 4)
    max_evidence_per_claim: int = int(_env("FACTCHECK_MAX_EVIDENCE", "10") or 10)
    http_timeout: float = float(_env("FACTCHECK_HTTP_TIMEOUT", "15") or 15)
    max_concurrency: int = int(_env("FACTCHECK_CONCURRENCY", "6") or 6)

    @property
    def llm_ready(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
