"""Wikipedia: search for titles, then pull intro extracts as evidence."""
from __future__ import annotations

from typing import List

from ..schemas import Evidence, SourceKind
from .base import Source, clean, ev_id, make_client

API = "https://en.wikipedia.org/w/api.php"


class WikipediaSource:
    name = "wikipedia"

    async def search(self, query: str, limit: int) -> List[Evidence]:
        async with make_client() as client:
            r = await client.get(
                API,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": limit,
                    "format": "json",
                },
            )
            r.raise_for_status()
            hits = r.json().get("query", {}).get("search", [])
            if not hits:
                return []
            titles = [h["title"] for h in hits]

            # Pull plaintext intros for all hit titles in one round-trip.
            r2 = await client.get(
                API,
                params={
                    "action": "query",
                    "prop": "extracts|info",
                    "exintro": 1,
                    "explaintext": 1,
                    "inprop": "url",
                    "titles": "|".join(titles),
                    "format": "json",
                },
            )
            r2.raise_for_status()
            pages = r2.json().get("query", {}).get("pages", {})

        out: List[Evidence] = []
        for page in pages.values():
            title = page.get("title", "")
            extract = page.get("extract", "")
            url = page.get("fullurl") or f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            if not extract:
                continue
            out.append(
                Evidence(
                    id=ev_id(self.name, url),
                    title=title,
                    snippet=clean(extract),
                    url=url,
                    source=self.name,
                    kind=SourceKind.encyclopedia,
                    query=query,
                )
            )
        return out
