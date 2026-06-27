"""Orchestrates the six-stage verification pipeline.

``run`` drives the whole flow and calls ``emit`` with structured progress
events after every meaningful step, so the API can stream the reasoning trace
to the front-end (and the CLI can print it).  Claims are processed concurrently
through plan -> retrieve -> assess -> aggregate.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, List, Optional

from .aggregate import aggregate, label
from .assess import assess_claim
from .claims import extract_claims
from .config import settings
from .llm import LLM
from .planner import plan_searches
from .report import build_report
from .retrieve import retrieve
from .schemas import ClaimResult, VerificationReport

Emit = Callable[[dict], Awaitable[None]]


async def _noop(_: dict) -> None:  # default sink
    return None


async def run(text: str, emit: Optional[Emit] = None) -> VerificationReport:
    emit = emit or _noop
    llm = LLM(settings.model)

    # --- Stage 1: extract claims -----------------------------------------
    await emit({"stage": "extract", "status": "start", "message": "抽取关键断言…"})
    claims = await extract_claims(text, llm)
    await emit(
        {
            "stage": "extract",
            "status": "done",
            "claims": [c.model_dump() for c in claims],
            "message": f"抽取到 {len(claims)} 条可核验断言",
        }
    )
    if not claims:
        report = VerificationReport(
            input_text=text, summary="未抽取到可核验的事实性断言(可能全为观点或无实质内容)。"
        )
        await emit({"stage": "done", "report": report.model_dump()})
        return report

    # --- Stages 2-5 per claim, concurrently ------------------------------
    sem = asyncio.Semaphore(settings.max_concurrency)

    async def process(claim) -> ClaimResult:
        async with sem:
            plan = await plan_searches(claim, llm)
            await emit(
                {
                    "stage": "plan",
                    "claim_id": claim.id,
                    "queries": plan.queries,
                    "sources": plan.sources,
                    "message": f"[{claim.id}] 规划 {len(plan.queries)} 条查询 → {', '.join(plan.sources)}",
                }
            )
            evidence = await retrieve(plan)
            await emit(
                {
                    "stage": "retrieve",
                    "claim_id": claim.id,
                    "count": len(evidence),
                    "message": f"[{claim.id}] 检索到 {len(evidence)} 条候选证据",
                }
            )
            assessed = await assess_claim(claim, evidence, llm, settings.max_evidence_per_claim)
            await emit(
                {
                    "stage": "assess",
                    "claim_id": claim.id,
                    "assessed": len(assessed),
                    "message": f"[{claim.id}] 研判 {len(assessed)} 条证据立场",
                }
            )
            result = aggregate(claim, assessed)
            await emit(
                {
                    "stage": "aggregate",
                    "claim_id": claim.id,
                    "result": result.model_dump(),
                    "message": f"[{claim.id}] 裁决:{label(result.verdict)}(可信度 {result.credibility})",
                }
            )
            return result

    results: List[ClaimResult] = await asyncio.gather(*[process(c) for c in claims])
    # Preserve original claim order in the report.
    order = {c.id: i for i, c in enumerate(claims)}
    results.sort(key=lambda r: order[r.claim.id])

    # --- Stage 6: report -------------------------------------------------
    await emit({"stage": "report", "status": "start", "message": "生成核验报告…"})
    report = await build_report(text, results, llm)
    await emit({"stage": "done", "report": report.model_dump(), "message": "核验完成"})
    return report
