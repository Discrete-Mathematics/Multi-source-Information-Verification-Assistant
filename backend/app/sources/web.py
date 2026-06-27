"""General web search via DuckDuckGo's HTML endpoint (no API key)."""
from __future__ import annotations

from typing import List
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..schemas import Evidence, SourceKind
from .base import Source, clean, ev_id, make_client

ENDPOINT = "https://html.duckduckgo.com/html/"


def _decode(href: str) -> str:
    """DDG wraps result links as /l/?uddg=<encoded-target>."""
    if "uddg=" in href:
        q = parse_qs(urlparse(href).query)
        if "uddg" in q:
            return q["uddg"][0]
    if href.startswith("//"):
        return "https:" + href
    return href


class WebSource:
    name = "web"

    async def search(self, query: str, limit: int) -> List[Evidence]:
        async with make_client() as client:
            # GET hits the no-JS results page directly; POST returns a 202
            # challenge page with no results.
            r = await client.get(ENDPOINT, params={"q": query, "kl": "us-en"})
            if r.status_code >= 400:
                return []
            soup = BeautifulSoup(r.text, "html.parser")

        out: List[Evidence] = []
        for result in soup.select("div.result")[: limit * 2]:
            a = result.select_one("a.result__a")
            snip = result.select_one(".result__snippet")
            if not a:
                continue
            url = _decode(a.get("href", ""))
            title = clean(a.get_text(), 300)
            snippet = clean(snip.get_text() if snip else title)
            if not url.startswith("http"):
                continue
            out.append(
                Evidence(
                    id=ev_id(self.name, url),
                    title=title,
                    snippet=snippet,
                    url=url,
                    source=self.name,
                    kind=SourceKind.web,
                    query=query,
                )
            )
            if len(out) >= limit:
                break
        return out
