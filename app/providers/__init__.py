"""
Provider factory — auto-selects best available LLM backend.

Priority:
  1. Ollama (local GPU) — if reachable
  2. Groq  (cloud free) — if GROQ_API_KEY set
  3. Mock  (dev only)   — fallback

Set MODEL_PROVIDER=ollama/groq/auto in .env.
"auto" picks Ollama when running, falls to Groq when laptop is off.
"""

import os
from typing import Optional
from app.config import settings
from app.providers.base_provider import BaseProvider
from app.providers.mock_provider import MockProvider
from app.providers.ollama_provider import OllamaProvider
from app.utils import logger

_provider: Optional[BaseProvider] = None
_provider_name: str = ""


async def _make_provider() -> BaseProvider:
    mode = (os.environ.get("MODEL_PROVIDER") or settings.model_provider or "auto").lower()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()

    if mode == "groq":
        if not groq_key:
            raise RuntimeError("MODEL_PROVIDER=groq but GROQ_API_KEY not set in .env")
        from app.providers.groq_provider import GroqProvider
        logger.info("Provider: Groq (forced)")
        return GroqProvider(groq_key)

    if mode == "ollama":
        p = OllamaProvider()
        ok = await p.health_check()
        if not ok:
            logger.warning("Ollama unreachable and MODEL_PROVIDER=ollama — is 'ollama serve' running?")
        else:
            logger.info("Provider: Ollama (local GPU)")
        return p

    # auto: try Ollama first, fall back to Groq
    ollama = OllamaProvider()
    ok = await ollama.health_check()
    if ok:
        logger.info("Provider: Ollama (auto-selected, GPU active)")
        return ollama

    if groq_key:
        from app.providers.groq_provider import GroqProvider
        logger.info("Provider: Groq (auto-fallback — Ollama not reachable)")
        return GroqProvider(groq_key)

    logger.warning("Provider: Mock (no Ollama, no GROQ_API_KEY — set one in .env)")
    return MockProvider()


async def get_provider() -> BaseProvider:
    """Return active provider, re-checking if Ollama came back online."""
    global _provider, _provider_name

    # Re-check on every call if in auto mode — handles laptop coming back online
    mode = (os.environ.get("MODEL_PROVIDER") or settings.model_provider or "auto").lower()
    if mode == "auto" and _provider_name == "groq":
        ollama = OllamaProvider()
        if await ollama.health_check():
            logger.info("Provider: Ollama back online — switching from Groq")
            _provider = ollama
            _provider_name = "ollama"
            return _provider

    if _provider is None:
        _provider = await _make_provider()
        _provider_name = _provider.name

    return _provider


def reset_provider():
    global _provider, _provider_name
    _provider = None
    _provider_name = ""


class ProviderFactory:
    @classmethod
    def list_providers(cls) -> list:
        key = os.environ.get("GROQ_API_KEY", "")
        available = ["ollama"]
        if key:
            available.append("groq")
        available.append("mock")
        return available
