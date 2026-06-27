"""
Ollama provider — uses /api/chat for proper multi-turn conversation.
"""

from typing import Optional, List
import aiohttp

from app.core import Message
from app.providers.base_provider import BaseProvider
from app.config import settings
from app.utils import logger


class OllamaProvider(BaseProvider):
    """Provider for Ollama local models."""

    def __init__(self):
        super().__init__("ollama")
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = 300  # 5 min for large models
        self._ghost_plan = None  # cached GhostPlan

    def _get_ghost_options(self, model: str, num_ctx: int) -> dict:
        """Get Ghost Engine + speed optimizer options for this model + hardware."""
        try:
            from app.hardware.ghost_engine import calculate_plan
            from app.hardware.speed_optimizer import speed_options
            plan = calculate_plan(model, requested_ctx=num_ctx)
            if plan.warnings:
                for w in plan.warnings:
                    logger.warning(f"GhostEngine: {w}")
            return speed_options(plan.ollama_options)
        except Exception as e:
            logger.debug(f"GhostEngine unavailable: {e}")
            return {"num_ctx": num_ctx}

    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        try:
            # Convert Message objects to Ollama chat format
            chat_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            chosen_model = self.model
            num_ctx = kwargs.get("num_ctx", 8192)
            ghost_opts = self._get_ghost_options(chosen_model, num_ctx)
            payload = {
                "model": chosen_model,
                "messages": chat_messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    **ghost_opts,
                },
            }
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama API error {response.status}: {error_text}")
                        return f"Error: Ollama returned {response.status} — is the model downloaded? Run: ollama pull {self.model}"

                    data = await response.json()
                    content = data.get("message", {}).get("content", "").strip()
                    if not content:
                        return "Error: Empty response from Ollama"
                    return content

        except aiohttp.ClientConnectorError:
            return (
                "Error: Cannot connect to Ollama. "
                "Start it with: ollama serve"
            )
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"Error: {str(e)}"

    async def stream_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        model: Optional[str] = None,
        num_ctx: int = 4096,
    ):
        """Async generator yielding token strings from Ollama streaming API."""
        chosen_model = model or self.model
        # Match the ctx the model is already running with — prevents Ollama reload (+30s)
        from app.hardware.speed_optimizer import get_warmed_ctx, KEEP_ALIVE_SECONDS
        effective_ctx = get_warmed_ctx(chosen_model, fallback=num_ctx)
        # Minimal options: only num_ctx + keep_alive. Any extra option (num_gpu, num_thread, etc.)
        # that differs from what Ollama loaded with causes a model reload — costing 30-40s.
        opts = {
            "temperature": temperature,
            "num_ctx": effective_ctx,
            "keep_alive": KEEP_ALIVE_SECONDS,
        }
        chat_messages = [{"role": m.role, "content": m.content} for m in messages]
        payload = {
            "model": chosen_model,
            "messages": chat_messages,
            "stream": True,
            "options": opts,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status != 200:
                        yield f"[Error {resp.status} from Ollama]"
                        return
                    async for line in resp.content:
                        line = line.strip()
                        if not line:
                            continue
                        import json
                        try:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if data.get("done"):
                                return
                        except Exception:
                            continue
        except aiohttp.ClientConnectorError:
            yield "[Error: Cannot connect to Ollama — run: ollama serve]"
        except Exception as e:
            yield f"[Error: {e}]"

    async def generate_with_tools(
        self,
        messages: List[Message],
        tools: list[dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        num_ctx: int = 8192,
    ) -> tuple[str, list[dict]]:
        """
        Send messages + tool specs. Returns (content, tool_calls).
        tool_calls: list of {name, arguments}
        Empty tool_calls means model answered directly in content.
        """
        chat_messages = [{"role": m.role, "content": m.content} for m in messages]
        payload = {
            "model": model or self.model,
            "messages": chat_messages,
            "tools": tools,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama tool-call error {response.status}: {error_text}")
                        return "", []
                    data = await response.json()
                    msg = data.get("message", {})
                    content = msg.get("content", "").strip()
                    raw_calls = msg.get("tool_calls", [])
                    tool_calls = [
                        {
                            "name": c["function"]["name"],
                            "arguments": c["function"].get("arguments", {}),
                        }
                        for c in raw_calls
                        if "function" in c
                    ]
                    return content, tool_calls
        except aiohttp.ClientConnectorError:
            return "", []
        except Exception as e:
            logger.error(f"generate_with_tools failed: {e}")
            return "", []

    async def list_models(self) -> list:
        """Return list of models available in Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []
