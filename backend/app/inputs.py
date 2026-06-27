"""Normalize the various input formats into plain text to verify.

Supported: raw text, a URL (fetch + extract readable text), or an uploaded
.txt/.md file (handled in main.py by reading bytes -> text).
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .sources.base import USER_AGENT


async def text_from_url(url: str, max_chars: int = 6000) -> str:
    async with httpx.AsyncClient(
        timeout=20, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    # Prefer <article>/<main> if present, else body.
    root = soup.find("article") or soup.find("main") or soup.body or soup
    paras = [p.get_text(" ", strip=True) for p in root.find_all(["p", "li"])]
    text = "\n".join(p for p in paras if len(p) > 40)
    if not text:
        text = root.get_text(" ", strip=True)
    return text[:max_chars].strip()
