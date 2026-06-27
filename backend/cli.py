"""CLI runner: python cli.py "<text to verify>"  (prints trace + markdown)."""
from __future__ import annotations

import asyncio
import sys

from app.pipeline import run


async def main(text: str) -> None:
    async def emit(ev: dict) -> None:
        msg = ev.get("message")
        if msg:
            print(f"  · {msg}")

    report = await run(text, emit)
    print("\n" + "=" * 70)
    print(report.markdown)


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else (
        "Transformer 模型由 Google 在 2017 年的论文《Attention Is All You Need》中提出,"
        "它完全摒弃了循环结构,仅依赖注意力机制。BERT 是第一个使用 Transformer 的模型。"
    )
    asyncio.run(main(text))
