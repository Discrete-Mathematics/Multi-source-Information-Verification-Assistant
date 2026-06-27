"""Crossref works API -> Evidence (mostly peer-reviewed journal/conf items)."""
from __future__ import annotations

import re
from typing import List

from ..schemas import Evidence, SourceKind
from .base import Source, clean, ev_id, make_client

API = "https://api.crossref.org/works"
_JATS = re.compile(r"<[^>]+>")


class CrossrefSource:
    name = "crossref"

    async def search(self, query: str, limit: int) -> List[Evidence]:
        async with make_client() as client:
            r = await client.get(
                API,
                params={"query": query, "rows": limit, "select": ",".join(
                    ["title", "abstract", "DOI", "URL", "author", "container-title",
                     "issued", "is-referenced-by-count", "type"]
                )},
            )
            if r.status_code >= 400:
                return []
            items = r.json().get("message", {}).get("items", [])

        out: List[Evidence] = []
        for it in items:
            title = " ".join(it.get("title", []) or [])
            abstract = _JATS.sub(" ", it.get("abstract", "") or "")
            url = it.get("URL") or (f"https://doi.org/{it['DOI']}" if it.get("DOI") else "")
            if not title or not url:
                continue
            venue = " ".join(it.get("container-title", []) or [])
            year = None
            issued = it.get("issued", {}).get("date-parts", [[None]])
            if issued and issued[0] and issued[0][0]:
                year = str(issued[0][0])
            authors = [
                " ".join(filter(None, [a.get("given"), a.get("family")]))
                for a in it.get("author", []) or []
            ]
            # Without an abstract, fall back to title-only snippet (still useful
            # for attribution/temporal claims).
            snippet = clean(abstract) if abstract else clean(f"{title}. {venue}.")
            out.append(
                Evidence(
                    id=ev_id(self.name, url),
                    title=clean(title, 300),
                    snippet=snippet,
                    url=url,
                    source=self.name,
                    kind=SourceKind.peer_reviewed,
                    published=year,
                    authors=[a for a in authors if a][:8] or None,
                    venue=venue or None,
                    citation_count=it.get("is-referenced-by-count"),
                    query=query,
                )
            )
        return out
