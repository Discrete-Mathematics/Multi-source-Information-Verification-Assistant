"""Stage 6 — assemble the cited verification report."""
from __future__ import annotations

from typing import Dict, List

from .aggregate import label
from .llm import LLM
from .schemas import (
    ClaimResult,
    Evidence,
    Stance,
    Verdict,
    VerificationReport,
)

_OVERALL_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}, "overall_verdict": {"type": "string"}},
    "required": ["summary", "overall_verdict"],
}


def _collect_sources(claims: List[ClaimResult]) -> Dict[str, int]:
    """Assign a stable citation number to each unique evidence url."""
    order: Dict[str, int] = {}
    for cr in claims:
        for a in cr.evidence:
            if a.evidence.id not in order:
                order[a.evidence.id] = len(order) + 1
    return order


def _overall_credibility(claims: List[ClaimResult]) -> float:
    """Checkworthiness × confidence weighted average of per-claim credibility."""
    num = den = 0.0
    for cr in claims:
        w = cr.claim.checkworthiness * (0.3 + 0.7 * cr.confidence)
        num += cr.credibility * w
        den += w
    return round(num / den, 1) if den else 50.0


async def build_report(
    input_text: str, claims: List[ClaimResult], llm: LLM
) -> VerificationReport:
    cite = _collect_sources(claims)
    id_to_ev: Dict[str, Evidence] = {
        a.evidence.id: a.evidence for cr in claims for a in cr.evidence
    }
    sources = [id_to_ev[i] for i, _ in sorted(cite.items(), key=lambda kv: kv[1])]
    overall_cred = _overall_credibility(claims)

    # One LLM call for a human-readable overall summary.
    verdict_lines = "\n".join(
        f"- [{label(cr.verdict)} | 可信度 {cr.credibility}] {cr.claim.text}" for cr in claims
    )
    try:
        data = await llm.structured(
            f"以下是对一段文本逐条断言核验的结果(整体可信度 {overall_cred}/100):\n\n"
            f"{verdict_lines}\n\n请用中文写一段简洁的总体核验结论(3-5句),"
            f"指出文本整体可信程度、最值得注意的问题或被反驳之处。",
            schema=_OVERALL_SCHEMA,
            tool_name="emit_summary",
            max_tokens=600,
        )
        summary = data.get("summary", "")
        overall_verdict = data.get("overall_verdict", "")
    except Exception:
        summary = "已完成逐条断言核验,详见下方各断言结论。"
        overall_verdict = f"整体可信度 {overall_cred}/100"

    report = VerificationReport(
        input_text=input_text,
        overall_verdict=overall_verdict,
        overall_credibility=overall_cred,
        summary=summary,
        claims=claims,
        sources=sources,
    )
    report.markdown = render_markdown(report, cite)
    return report


def _stance_zh(s: Stance) -> str:
    return {"supports": "支持", "refutes": "反驳", "neutral": "中立"}[s.value]


def render_markdown(report: VerificationReport, cite: Dict[str, int]) -> str:
    L: List[str] = []
    L.append("# 信息核验报告\n")
    L.append(f"**整体可信度**:{report.overall_credibility}/100  ")
    L.append(f"**总体结论**:{report.overall_verdict}\n")
    L.append(f"> {report.summary}\n")
    L.append("---\n")
    L.append("## 原文\n")
    L.append(f"> {report.input_text}\n")
    L.append("## 逐条断言核验\n")
    for i, cr in enumerate(report.claims, 1):
        L.append(f"### {i}. {cr.claim.text}\n")
        L.append(
            f"- **裁决**:{label(cr.verdict)}　**可信度**:{cr.credibility}/100"
            f"　**置信度**:{cr.confidence}　**类型**:{cr.claim.type.value}"
        )
        L.append(f"- **说明**:{cr.explanation}")
        if cr.evidence:
            L.append("- **证据**:")
            for a in cr.evidence:
                n = cite.get(a.evidence.id, 0)
                note = f" — {a.note}" if a.note else ""
                L.append(
                    f"    - [{n}] ({_stance_zh(a.stance)}, 权重 {a.weight}) "
                    f"{a.evidence.title}{note}"
                )
        L.append("")
    L.append("## 引用来源\n")
    for ev in report.sources:
        n = cite.get(ev.id, 0)
        meta = ev.source
        if ev.published:
            meta += f", {ev.published}"
        L.append(f"[{n}] {ev.title} ({meta}). {ev.url}")
    return "\n".join(L)
