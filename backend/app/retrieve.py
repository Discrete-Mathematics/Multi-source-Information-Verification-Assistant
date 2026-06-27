"""Stage 3 — execute a SearchPlan concurrently and dedup evidence."""
from __future__ import annotations

import asyncio
from typing import Dict, List

from .config import settings
from .schemas import Evidence, SearchPlan
from .sources import get_source


async def retrieve(plan: SearchPlan) -> List[Evidence]:
    sem = asyncio.Semaphore(settings.max_concurrency)

    async def one(source_name: str, query: str) -> List[Evidence]:
        src = get_source(source_name)
        if src is None:
            return []
        async with sem:
            try:
                return await src.search(query, settings.evidence_per_query)
            except Exception:
                # A single source/query failing must not sink the claim.
                return []

    tasks = [one(s, q) for q in plan.queries for s in plan.sources]
    results = await asyncio.gather(*tasks)

    # Dedup by evidence id (source+url hash), keep first occurrence.
    merged: Dict[str, Evidence] = {}
    for batch in results:
        for ev in batch:
            merged.setdefault(ev.id, ev)
    return list(merged.values())
