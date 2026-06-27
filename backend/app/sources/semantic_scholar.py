"""Semantic Scholar graph API.

The key-free pool is heavily rate-limited (429).  We retry with backoff and, on
persistent failure, return [] so one flaky source never sinks the pipeline.
"""
from __future__ import annotations

import asyncio
from typing import List

from ..schemas import Evidence, SourceKind
from .base import Source, clean, ev_id, make_client

API = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,url,year,authors,venue,citationCount,publicationVenue,isOpenAccess"


class SemanticScholarSource:
    name = "semantic_scholar"

    async def search(self, query: str, limit: int) -> List[Evidence]:
        async with make_client() as client:
            data = None
            for attempt in range(3):
                r = await client.get(
                    API, params={"query": query, "limit": limit, "fields": FIELDS}
                )
                if r.status_code == 429:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                if r.status_code >= 400:
                    return []
                data = r.json()
                break
            if data is None:
                return []

        out: List[Evidence] = []
        for p in data.get("data", []) or []:
            abstract = p.get("abstract")
            if not abstract:
                continue
            url = p.get("url") or ""
            venue = (p.get("venue") or "") or (p.get("publicationVenue") or {}).get("name", "")
            # A real venue implies peer review; otherwise treat as preprint-ish.
            kind = SourceKind.peer_reviewed if venue else SourceKind.preprint
            out.append(
                Evidence(
                    id=ev_id(self.name, url or p.get("paperId", query)),
                    title=clean(p.get("title", ""), 300),
                    snippet=clean(abstract),
                    url=url,
                    source=self.name,
                    kind=kind,
                    published=str(p.get("year")) if p.get("year") else None,
                    authors=[a.get("name") for a in (p.get("authors") or [])][:8] or None,
                    venue=venue or None,
                    citation_count=p.get("citationCount"),
                    query=query,
                )
            )
        return out
