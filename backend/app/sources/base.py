"""Source protocol + shared HTTP helpers."""
from __future__ import annotations

import hashlib
from typing import List, Protocol, runtime_checkable

import httpx

from ..config import settings
from ..schemas import Evidence

USER_AGENT = "FactCheckAssistant/1.0 (research demo; mailto:demo@example.com)"


@runtime_checkable
class Source(Protocol):
    name: str

    async def search(self, query: str, limit: int) -> List[Evidence]:
        ...


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=settings.http_timeout,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def ev_id(source: str, url: str) -> str:
    return f"{source}-{hashlib.sha1(url.encode()).hexdigest()[:10]}"


def clean(text: str, limit: int = 600) -> str:
    text = " ".join((text or "").split())
    return text[:limit]
