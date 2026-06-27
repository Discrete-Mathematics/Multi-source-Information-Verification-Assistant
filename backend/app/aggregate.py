"""Stage 5 — aggregate assessed evidence into a per-claim verdict + score.

The verdict and the 0-100 credibility are computed by an explicit, auditable
formula rather than by asking the model "is this true?".  Intuition:

    credibility = 50 + (support_ratio - 0.5) * 100 * strength

* support_ratio in [0,1] is the share of (weighted) evidence that supports.
* strength in [0,1] grows with the *total* relevant evidence weight, so a claim
  backed by one weak web page stays near 50 ("uncertain"), while a claim with
  several strong, consistent sources moves decisively toward 0 or 100.

This makes the score move for two independent reasons — direction *and* amount
of evidence — which is exactly what a human fact-checker weighs.
"""
from __future__ import annotations

from typing import List

from .schemas import AssessedEvidence, Claim, ClaimResult, Stance, Verdict

# Total weight at which we consider the evidence base "saturated".
_REF_WEIGHT = 1.2
_MIN_WEIGHT = 0.25  # below this, we don't have enough to rule

_VERDICT_LABEL = {
    Verdict.supported: "证据支持",
    Verdict.refuted: "证据反驳",
    Verdict.partially_supported: "部分支持",
    Verdict.conflicting: "证据冲突",
    Verdict.insufficient: "证据不足",
}


def label(v: Verdict) -> str:
    return _VERDICT_LABEL[v]


def aggregate(claim: Claim, assessed: List[AssessedEvidence]) -> ClaimResult:
    support = sum(a.weight for a in assessed if a.stance == Stance.supports)
    refute = sum(a.weight for a in assessed if a.stance == Stance.refutes)
    total = support + refute
    strength = min(1.0, total / _REF_WEIGHT)

    if total < _MIN_WEIGHT:
        verdict = Verdict.insufficient
        credibility = 50.0
    else:
        ratio = support / total
        credibility = max(0.0, min(100.0, 50 + (ratio - 0.5) * 100 * strength))
        minority = min(support, refute)
        if minority >= 0.35 * total and total >= 0.5:
            verdict = Verdict.conflicting
        elif ratio >= 0.70:
            verdict = Verdict.supported
        elif ratio <= 0.30:
            verdict = Verdict.refuted
        else:
            verdict = Verdict.partially_supported

    return ClaimResult(
        claim=claim,
        verdict=verdict,
        credibility=round(credibility, 1),
        confidence=round(strength, 2),
        support_weight=round(support, 3),
        refute_weight=round(refute, 3),
        explanation=_explain(verdict, assessed, support, refute),
        evidence=assessed,
    )


def _explain(
    verdict: Verdict, assessed: List[AssessedEvidence], support: float, refute: float
) -> str:
    sup = [a for a in assessed if a.stance == Stance.supports]
    ref = [a for a in assessed if a.stance == Stance.refutes]
    parts: List[str] = [
        f"判定为「{label(verdict)}」:支持权重 {support:.2f} / 反驳权重 {refute:.2f}"
        f"(共 {len(assessed)} 条相关证据)。"
    ]
    if sup:
        top = sup[0]
        parts.append(f"最强支持证据来自 {top.evidence.source}《{top.evidence.title}》。")
    if ref:
        top = ref[0]
        parts.append(f"最强反驳证据来自 {top.evidence.source}《{top.evidence.title}》。")
    if verdict == Verdict.conflicting:
        parts.append("不同高质量来源给出矛盾结论,需人工进一步判读。")
    if verdict == Verdict.insufficient:
        parts.append("未检索到足够强相关的证据,无法判定。")
    return "".join(parts)
