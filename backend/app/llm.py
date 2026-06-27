"""Minimal async Anthropic client.

We talk to the Messages API directly over httpx instead of the SDK so the app
stays robust against proxy/SDK version drift (this environment routes through a
cloudflare proxy base_url).  Two entry points:

* ``complete``    -> free-form text
* ``structured``  -> forces a tool call whose input matches a JSON Schema, so
                     callers get validated structured data back without praying
                     that the model returned clean JSON.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from .config import settings


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or settings.model
        self._base = settings.anthropic_base_url.rstrip("/")
        self._headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def _post(self, payload: Dict[str, Any], timeout: float = 120.0) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(3):
                try:
                    r = await client.post(
                        f"{self._base}/v1/messages", headers=self._headers, json=payload
                    )
                    if r.status_code == 429 or r.status_code >= 500:
                        raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
                    r.raise_for_status()
                    return r.json()
                except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                    if attempt == 2:
                        raise LLMError(f"LLM request failed: {exc}") from exc
        raise LLMError("unreachable")

    async def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 1500,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        data = await self._post(payload)
        return _first_text(data)

    async def structured(
        self,
        prompt: str,
        *,
        schema: Dict[str, Any],
        tool_name: str = "emit",
        tool_description: str = "Return the structured result.",
        system: Optional[str] = None,
        max_tokens: int = 2500,
    ) -> Dict[str, Any]:
        """Force a single tool call whose `input` conforms to `schema`."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [
                {"name": tool_name, "description": tool_description, "input_schema": schema}
            ],
            "tool_choice": {"type": "tool", "name": tool_name},
        }
        if system:
            payload["system"] = system
        data = await self._post(payload)
        for block in data.get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == tool_name:
                return block.get("input", {})
        # Fallback: model returned text JSON despite tool_choice.
        text = _first_text(data)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"structured() got no tool_use and unparseable text: {text[:200]}") from exc


def _first_text(data: Dict[str, Any]) -> str:
    parts: List[str] = [
        b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
    ]
    return "\n".join(p for p in parts if p).strip()
