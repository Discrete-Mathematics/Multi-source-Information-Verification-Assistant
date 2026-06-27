"""Stage 2 — turn each claim into search queries and route to sources.

Routing is claim-type aware: research/temporal/attribution claims about papers
go to academic indices; everything also gets a general web+encyclopedia pass so
we never rely on a single source family.
"""
from __future__ import annotations

from typing import List

from .llm import LLM
from .schemas import Claim, ClaimType, SearchPlan
from .sources import ACADEMIC_SOURCES, GENERAL_SOURCES
from .config import settings

_ACADEMIC_TYPES = {
    ClaimType.research_finding,
    ClaimType.statistical,
    ClaimType.causal,
}

_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "差异化的英文检索查询(关键词式,非整句)",
        }
    },
    "required": ["queries"],
}

_PROMPT = """为核验下面这条断言,生成 {n} 条**差异化**的检索查询。
- 用英文关键词(学术与网络检索召回更好);
- 各条覆盖不同角度(核心概念 / 反面证据 / 具体实体或数字);
- 不要整句照抄,提炼可检索的关键词。

断言:{claim}
类型:{ctype}"""


def _route(claim: Claim) -> List[str]:
    sources = list(GENERAL_SOURCES)
    if claim.type in _ACADEMIC_TYPES or claim.type == ClaimType.attribution:
        sources = ACADEMIC_SOURCES + GENERAL_SOURCES
    if claim.type == ClaimType.definitional:
        sources = ["wikipedia"] + GENERAL_SOURCES
    # de-dup, preserve order
    seen, out = set(), []
    for s in sources:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


async def plan_searches(claim: Claim, llm: LLM | None = None) -> SearchPlan:
    llm = llm or LLM()
    data = await llm.structured(
        _PROMPT.format(n=settings.queries_per_claim, claim=claim.text, ctype=claim.type.value),
        schema=_SCHEMA,
        tool_name="emit_queries",
        max_tokens=400,
    )
    queries = [q.strip() for q in data.get("queries", []) if q.strip()]
    if not queries:
        queries = [claim.text]
    return SearchPlan(
        claim_id=claim.id,
        queries=queries[: settings.queries_per_claim],
        sources=_route(claim),
    )
