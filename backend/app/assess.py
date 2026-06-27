"""Stage 4 — assess each evidence item against a claim.

Split of responsibility (deliberate, and a talking point in the design doc):

* The **LLM** judges what it is good at: stance (supports/refutes/neutral),
  how relevant the snippet is, and a one-line reason.  This is an NLI-style
  judgement, done in one batched call per claim.
* **Deterministic code** scores what should not be left to a model's whim:
  source quality (from source kind / venue / citations) and recency (from the
  publication date).  This keeps scoring auditable and reproducible.

The final per-evidence ``weight`` combines them.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Dict, List

from .llm import LLM
from .schemas import AssessedEvidence, Claim, Evidence, SourceKind, Stance

_CURRENT_YEAR = datetime.now().year

_QUALITY_BASE = {
    SourceKind.peer_reviewed: 0.85,
    SourceKind.encyclopedia: 0.70,
    SourceKind.preprint: 0.60,
    SourceKind.web: 0.40,
}

_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _quality(ev: Evidence) -> float:
    q = _QUALITY_BASE.get(ev.kind, 0.4)
    if ev.citation_count:
        q += min(0.12, math.log10(ev.citation_count + 1) * 0.04)
    return max(0.0, min(1.0, q))


def _recency(ev: Evidence) -> float:
    if not ev.published:
        return 0.55  # unknown date -> mildly neutral
    m = _YEAR_RE.search(ev.published)
    if not m:
        return 0.55
    age = _CURRENT_YEAR - int(m.group(0))
    return max(0.30, min(1.0, 1.0 - age / 20.0))


def _select(evidence: List[Evidence], cap: int) -> List[Evidence]:
    """Round-robin across sources so no single source dominates the cap."""
    by_src: Dict[str, List[Evidence]] = {}
    for ev in evidence:
        by_src.setdefault(ev.source, []).append(ev)
    out: List[Evidence] = []
    while len(out) < cap and any(by_src.values()):
        for src in list(by_src.keys()):
            if by_src[src]:
                out.append(by_src[src].pop(0))
                if len(out) >= cap:
                    break
    return out


_SCHEMA = {
    "type": "object",
    "properties": {
        "judgements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "stance": {"type": "string", "enum": [s.value for s in Stance]},
                    "stance_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "relevance": {"type": "number", "minimum": 0, "maximum": 1},
                    "note": {"type": "string", "description": "为何支持/反驳/无关(一句话)"},
                },
                "required": ["index", "stance", "stance_confidence", "relevance"],
            },
        }
    },
    "required": ["judgements"],
}

_SYSTEM = """你是事实核查中的证据研判员。对每条证据,判断它相对于"断言"的立场:
- supports: 证据内容支持断言为真;
- refutes: 证据内容与断言矛盾,支持断言为假;
- neutral: 证据相关但不能判定,或与断言无关。
relevance 衡量证据与断言的主题相关度。stance_confidence 是你对立场判断的置信度。
只依据给定的证据片段判断,不要使用片段之外的知识。证据可能是英文,断言可能是中文,请跨语言对照。"""


def _format_evidence(evs: List[Evidence]) -> str:
    lines = []
    for i, ev in enumerate(evs):
        meta = f"[{ev.source}/{ev.kind.value}"
        if ev.published:
            meta += f", {ev.published}"
        meta += "]"
        lines.append(f"#{i} {meta} {ev.title}\n   {ev.snippet}")
    return "\n".join(lines)


async def assess_claim(
    claim: Claim, evidence: List[Evidence], llm: LLM, cap: int
) -> List[AssessedEvidence]:
    evs = _select(evidence, cap)
    if not evs:
        return []

    prompt = (
        f"断言:{claim.text}\n\n以下是检索到的证据(编号 #index):\n\n"
        f"{_format_evidence(evs)}\n\n请对每条证据给出立场研判。"
    )
    data = await llm.structured(
        prompt, schema=_SCHEMA, system=_SYSTEM, tool_name="emit_judgements", max_tokens=2500
    )
    judge_by_idx = {j["index"]: j for j in data.get("judgements", [])}

    assessed: List[AssessedEvidence] = []
    for i, ev in enumerate(evs):
        j = judge_by_idx.get(i, {})
        try:
            stance = Stance(j.get("stance", "neutral"))
        except ValueError:
            stance = Stance.neutral
        relevance = float(j.get("relevance", 0.0))
        conf = float(j.get("stance_confidence", 0.0))
        quality = _quality(ev)
        recency = _recency(ev)
        # Old but strong work shouldn't be destroyed -> dampen recency factor.
        weight = relevance * quality * (0.6 + 0.4 * recency) * conf
        assessed.append(
            AssessedEvidence(
                evidence=ev,
                stance=stance,
                stance_confidence=conf,
                relevance=relevance,
                quality=round(quality, 3),
                recency=round(recency, 3),
                weight=round(weight, 4),
                note=j.get("note"),
            )
        )
    # Most informative first.
    assessed.sort(key=lambda a: a.weight, reverse=True)
    return assessed
