"""
OpenRouter provider — 200+ models via single API key, OpenAI-compatible.
Free models (`:free` suffix) have no cost. Paid models billed per token.

Get key: https://openrouter.ai/keys
Free models: meta-llama/llama-3.1-8b-instruct:free, google/gemma-2-9b-it:free, etc.
"""

import json
import os
from typing import List, Optional

import aiohttp

from app.core import Message
from app.providers.base_provider import BaseProvider
from app.utils import logger

_API_URL = "https://openrouter.ai/api/v1/chat/completions"

_FREE_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
]


def _pick_model(requested: str | None = None) -> str:
    env = os.environ.get("OPENROUTER_MODEL", "").strip()
    candidate = requested or env or _FREE_MODELS[0]
    # Reject Ollama-style names (contain ":")  unless they're OpenRouter :free models
    if ":" in candidate and not candidate.endswith(":free"):
        candidate = env or _FREE_MODELS[0]
    return candidate


class OpenRouterProvider(BaseProvider):
    """OpenRouter cloud LLM — 200+ models, free tier available."""

    def __init__(self, api_key: str):
        super().__init__("openrouter")
        self.api_key = api_key
        self.timeout = 120

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://illip.ai",
            "X-Title": "ILLIP AI",
        }

    def _to_messages(self, messages: List[Message]) -> list:
        return [{"role": m.role if m.role != "tool" else "user", "content": m.content}
                for m in messages]

    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    "https://openrouter.ai/api/v1/models",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as r:
                    return r.status == 200
        except Exception:
            return False

    async def generate_response(self, messages: List[Message], temperature: float = 0.7,
                                max_tokens: Optional[int] = None, **kwargs) -> str:
        payload = {
            "model": _pick_model(kwargs.get("model")),
            "messages": self._to_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens or 2048,
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    _API_URL, json=payload, headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as r:
                    if r.status != 200:
                        return f"OpenRouter error {r.status}: {await r.text()}"
                    d = await r.json()
                    return d["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"OpenRouter error: {e}"

    async def stream_response(self, messages: List[Message], temperature: float = 0.7,
                              model: Optional[str] = None, num_ctx: int = 4096):
        chosen = _pick_model(model)
        payload = {
            "model": chosen,
            "messages": self._to_messages(messages),
            "temperature": temperature,
            "max_tokens": 2048,
            "stream": True,
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    _API_URL, json=payload, headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        yield f"[OpenRouter error {resp.status}]"
                        return
                    async for line in resp.content:
                        line = line.decode().strip()
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            return
                        try:
                            chunk = json.loads(data)
                            token = chunk["choices"][0].get("delta", {}).get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue
        except aiohttp.ClientConnectorError:
            yield "[OpenRouter unreachable — check OPENROUTER_API_KEY]"
        except Exception as e:
            yield f"[OpenRouter error: {e}]"

    async def generate_with_tools(self, messages: List[Message], tools: list,
                                   temperature: float = 0.7, model: Optional[str] = None,
                                   num_ctx: int = 4096) -> tuple[str, list]:
        payload = {
            "model": _pick_model(model),
            "messages": self._to_messages(messages),
            "tools": tools,
            "tool_choice": "auto",
            "temperature": temperature,
            "max_tokens": 2048,
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    _API_URL, json=payload, headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        return "", []
                    d = await resp.json()
                    msg = d["choices"][0]["message"]
                    content = msg.get("content") or ""
                    raw_calls = msg.get("tool_calls") or []
                    tool_calls = [
                        {
                            "name": c["function"]["name"],
                            "arguments": json.loads(c["function"].get("arguments", "{}")),
                        }
                        for c in raw_calls
                        if c.get("type") == "function"
                    ]
                    return content.strip(), tool_calls
        except Exception as e:
            logger.error(f"OpenRouter tool-call failed: {e}")
            return "", []
