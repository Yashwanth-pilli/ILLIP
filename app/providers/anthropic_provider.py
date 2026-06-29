"""
Anthropic Claude provider — native SDK, full streaming + tool use.

Models (set ANTHROPIC_MODEL in .env):
  claude-sonnet-4-6          — default, best quality
  claude-haiku-4-5-20251001  — fast, cheap, great for routing
  claude-opus-4-8            — max capability, slower

Get key: https://console.anthropic.com → API Keys
"""

import os
from typing import List, Optional, AsyncIterator

from app.core import Message
from app.providers.base_provider import BaseProvider
from app.utils import logger

_DEFAULT_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 8096


def _get_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL


def _split_system(messages: List[Message]) -> tuple[str, list]:
    """Extract system prompt and return (system_text, chat_messages)."""
    system_parts = []
    chat = []
    for m in messages:
        if m.role == "system":
            system_parts.append(m.content)
        else:
            chat.append(m)
    return "\n\n".join(system_parts), chat


def _to_anthropic_messages(messages: List[Message]) -> list:
    """Convert Message list → Anthropic messages format (no system role)."""
    result = []
    for m in messages:
        if m.role == "system":
            continue
        role = "user" if m.role in ("user", "tool") else "assistant"
        result.append({"role": role, "content": m.content})
    # Anthropic requires alternating user/assistant; merge consecutive same-role
    merged = []
    for msg in result:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n" + msg["content"]
        else:
            merged.append(msg)
    return merged


def _openai_tools_to_anthropic(tools: list) -> list:
    """Convert OpenAI function-calling format → Anthropic tools format."""
    out = []
    for t in tools:
        fn = t.get("function", t)  # handle both {function: ...} and flat
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return out


class AnthropicProvider(BaseProvider):
    """Anthropic Claude — streaming, tool use, multi-turn conversation."""

    def __init__(self, api_key: str):
        super().__init__("anthropic")
        self.api_key = api_key
        self.model = _get_model()

    def _client(self):
        try:
            import anthropic
            return anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic"
            )

    async def health_check(self) -> bool:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            # Minimal call to verify key works
            await client.models.list()
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.debug(f"Anthropic health check: {e}")
            return False

    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        system, chat = _split_system(messages)
        anthropic_msgs = _to_anthropic_messages(messages)
        if not anthropic_msgs:
            return ""

        try:
            client = self._client()
            kwargs_extra: dict = {}
            if system:
                kwargs_extra["system"] = system

            response = await client.messages.create(
                model=kwargs.get("model") or self.model,
                max_tokens=max_tokens or _MAX_TOKENS,
                temperature=temperature,
                messages=anthropic_msgs,
                **kwargs_extra,
            )
            # Extract text from content blocks
            parts = [b.text for b in response.content if hasattr(b, "text")]
            return "".join(parts).strip()
        except Exception as e:
            logger.error(f"Anthropic generate_response error: {e}")
            return f"Anthropic error: {e}"

    async def stream_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        model: Optional[str] = None,
        num_ctx: int = 8096,
    ) -> AsyncIterator[str]:
        system, _ = _split_system(messages)
        anthropic_msgs = _to_anthropic_messages(messages)
        if not anthropic_msgs:
            return

        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            kwargs_extra: dict = {}
            if system:
                kwargs_extra["system"] = system

            async with client.messages.stream(
                model=model or self.model,
                max_tokens=num_ctx or _MAX_TOKENS,
                temperature=temperature,
                messages=anthropic_msgs,
                **kwargs_extra,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except ImportError:
            yield "[anthropic not installed — pip install anthropic]"
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}")
            yield f"[Anthropic error: {e}]"

    async def generate_with_tools(
        self,
        messages: List[Message],
        tools: list,
        temperature: float = 0.7,
        model: Optional[str] = None,
        num_ctx: int = 8096,
    ) -> tuple[str, list]:
        """
        Tool-call round. Returns (content_text, tool_calls).
        tool_calls: [{"name": str, "arguments": dict}]
        Empty list → model answered directly.
        """
        system, _ = _split_system(messages)
        anthropic_msgs = _to_anthropic_messages(messages)
        if not anthropic_msgs:
            return "", []

        anthropic_tools = _openai_tools_to_anthropic(tools)

        try:
            client = self._client()
            kwargs_extra: dict = {}
            if system:
                kwargs_extra["system"] = system

            response = await client.messages.create(
                model=model or self.model,
                max_tokens=num_ctx or _MAX_TOKENS,
                temperature=temperature,
                messages=anthropic_msgs,
                tools=anthropic_tools,
                tool_choice={"type": "auto"},
                **kwargs_extra,
            )

            text_parts = []
            tool_calls = []

            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append({
                        "name": block.name,
                        "arguments": block.input or {},
                    })

            return "".join(text_parts).strip(), tool_calls

        except Exception as e:
            logger.error(f"Anthropic tool-call error: {e}")
            return "", []
