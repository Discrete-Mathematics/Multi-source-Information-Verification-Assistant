"""arXiv Atom API -> Evidence (preprints)."""
from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from ..schemas import Evidence, SourceKind
from .base import Source, clean, ev_id, make_client

API = "https://export.arxiv.org/api/query"


class ArxivSource:
    name = "arxiv"

    async def search(self, query: str, limit: int) -> List[Evidence]:
        async with make_client() as client:
            r = await client.get(
                API,
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": limit,
                    "sortBy": "relevance",
                },
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "xml")

        out: List[Evidence] = []
        for entry in soup.find_all("entry"):
            title = clean(entry.title.text if entry.title else "", 300)
            summary = entry.summary.text if entry.summary else ""
            url = entry.id.text if entry.id else ""
            published = entry.published.text[:10] if entry.published else None
            authors = [a.find("name").text for a in entry.find_all("author") if a.find("name")]
            if not url:
                continue
            out.append(
                Evidence(
                    id=ev_id(self.name, url),
                    title=title,
                    snippet=clean(summary),
                    url=url,
                    source=self.name,
                    kind=SourceKind.preprint,
                    published=published,
                    authors=authors[:8] or None,
                    venue="arXiv",
                    query=query,
                )
            )
        return out
