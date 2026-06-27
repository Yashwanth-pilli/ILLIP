"""
Groq provider — cloud LLM via Groq API (free tier).
Models: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768

Used as fallback when Ollama is not reachable (laptop off, no GPU).
Groq is free at groq.com — 14k tokens/min on free tier.
"""

import json
from typing import List, Optional
import aiohttp

from app.core import Message
from app.providers.base_provider import BaseProvider
from app.utils import logger

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model priority: best quality first, falls back to faster model
_MODEL_PRIORITY = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
]


def _pick_groq_model(requested: str | None = None) -> str:
    """Pick a Groq model. Ignores Ollama model names (e.g. qwen2.5:3b)."""
    import os
    env_model = os.environ.get("GROQ_MODEL", "")
    candidate = requested or env_model or _MODEL_PRIORITY[0]
    # Ollama models contain ":" (e.g. qwen2.5:3b) — reject them
    if candidate and ":" in candidate:
        candidate = env_model or _MODEL_PRIORITY[0]
    return candidate


class GroqProvider(BaseProvider):
    """Groq cloud LLM — streaming, free tier, OpenAI-compatible API."""

    def __init__(self, api_key: str):
        super().__init__("groq")
        self.api_key = api_key
        self.model = _pick_groq_model()
        self.timeout = 120

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _to_messages(self, messages: List[Message]) -> list:
        return [{"role": m.role if m.role != "tool" else "user", "content": m.content}
                for m in messages]

    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    "https://api.groq.com/openai/v1/models",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as r:
                    return r.status == 200
        except Exception:
            return False

    async def generate_response(self, messages: List[Message], temperature: float = 0.7,
                                 max_tokens: Optional[int] = None, **kwargs) -> str:
        payload = {
            "model": _pick_groq_model(kwargs.get("model")),
            "messages": self._to_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens or 2048,
            "stream": False,
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    _GROQ_API_URL, json=payload, headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as r:
                    if r.status != 200:
                        return f"Groq error {r.status}: {await r.text()}"
                    d = await r.json()
                    return d["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Groq error: {e}"

    async def stream_response(self, messages: List[Message], temperature: float = 0.7,
                               model: Optional[str] = None, num_ctx: int = 4096):
        chosen = _pick_groq_model(model)
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
                    _GROQ_API_URL, json=payload, headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        yield f"[Groq error {resp.status}]"
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
            yield "[Groq unreachable — check GROQ_API_KEY]"
        except Exception as e:
            yield f"[Groq error: {e}]"

    async def generate_with_tools(self, messages: List[Message], tools: list,
                                   temperature: float = 0.7, model: Optional[str] = None,
                                   num_ctx: int = 4096) -> tuple[str, list]:
        """Groq tool-call support via OpenAI function-calling format."""
        groq_tools = []
        for t in tools:
            groq_tools.append({
                "type": "function",
                "function": {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "parameters": t["function"].get("parameters", {}),
                }
            })
        payload = {
            "model": _pick_groq_model(model),
            "messages": self._to_messages(messages),
            "tools": groq_tools,
            "tool_choice": "auto",
            "temperature": temperature,
            "max_tokens": 2048,
            "stream": False,
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    _GROQ_API_URL, json=payload, headers=self._headers(),
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
            logger.error(f"Groq tool-call failed: {e}")
            return "", []
