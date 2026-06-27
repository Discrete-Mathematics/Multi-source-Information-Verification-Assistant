"""Stage 1 — decompose input text into atomic, check-worthy claims."""
from __future__ import annotations

from typing import List

from .config import settings
from .llm import LLM
from .schemas import Claim, ClaimType

_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "自包含、消解了指代的原子断言"},
                    "type": {
                        "type": "string",
                        "enum": [t.value for t in ClaimType],
                    },
                    "checkworthiness": {"type": "number", "minimum": 0, "maximum": 1},
                    "source_span": {"type": "string", "description": "原文对应片段"},
                    "rationale": {"type": "string", "description": "为何这样拆分/为何值得核验(简短)"},
                },
                "required": ["text", "type", "checkworthiness"],
            },
        }
    },
    "required": ["claims"],
}

_SYSTEM = """你是事实核查的断言抽取专家。把输入文本分解为可独立核验的"原子断言"。
规则:
1. 每条断言只包含一个可验证的事实点;复合句要拆开。
2. 消解指代与省略,使每条断言脱离上下文仍然完整(把"它/该模型/这项研究"替换为具体对象)。
3. 用原文语言表述断言。
4. 给纯主观观点、价值判断、修辞 type=opinion 且 checkworthiness 很低。
5. checkworthiness 衡量"核验该断言的价值与可行性":含具体数字、研究结论转述、可被外部来源证实/证伪的事实给高分。
6. 不要臆造原文没有的断言。"""

_PROMPT = """请从下面的文本中抽取需要核验的关键断言:

<text>
{text}
</text>

最多抽取 {max_claims} 条最值得核验的断言(按 checkworthiness 优先)。"""


async def extract_claims(text: str, llm: LLM | None = None) -> List[Claim]:
    llm = llm or LLM()
    data = await llm.structured(
        _PROMPT.format(text=text.strip(), max_claims=settings.max_claims),
        schema=_SCHEMA,
        system=_SYSTEM,
        tool_name="emit_claims",
        tool_description="返回抽取出的断言列表。",
        max_tokens=2500,
    )
    raw = data.get("claims", [])
    claims: List[Claim] = []
    for i, c in enumerate(raw):
        try:
            ctype = ClaimType(c.get("type", "general_fact"))
        except ValueError:
            ctype = ClaimType.general_fact
        claims.append(
            Claim(
                id=f"c{i+1}",
                text=c["text"].strip(),
                type=ctype,
                checkworthiness=float(c.get("checkworthiness", 0.5)),
                source_span=c.get("source_span"),
                rationale=c.get("rationale"),
            )
        )
    # Keep check-worthy claims; drop pure opinions. Sort by worthiness, cap.
    claims = [c for c in claims if c.checkworthiness >= 0.25 and c.type != ClaimType.opinion]
    claims.sort(key=lambda c: c.checkworthiness, reverse=True)
    return claims[: settings.max_claims]
