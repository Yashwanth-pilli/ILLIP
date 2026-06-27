"""
SearXNG search bridge — private local web search.
Falls back gracefully when SearXNG is not running.

To install SearXNG locally:
  docker run -d -p 8888:8080 --name searxng searxng/searxng
Then set SEARXNG_URL=http://localhost:8888 in .env
"""

import asyncio
from typing import Optional
import aiohttp
from app.config import settings
from app.utils import logger

# Default SearXNG URL — override with SEARXNG_URL env var
_SEARXNG_URL = getattr(settings, "searxng_url", "http://localhost:8888")


async def searxng_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search via SearXNG. Returns list of {title, url, snippet}.
    Returns [] if SearXNG unavailable (caller handles fallback).
    """
    try:
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_SEARXNG_URL}/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=8),
                headers={"Accept": "application/json"},
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"SearXNG returned {resp.status}")
                    return []
                data = await resp.json()
                results = []
                for r in data.get("results", [])[:max_results]:
                    results.append({
                        "title":   r.get("title", ""),
                        "url":     r.get("url", ""),
                        "snippet": r.get("content", ""),
                    })
                return results
    except aiohttp.ClientConnectorError:
        logger.debug("SearXNG not running — search unavailable")
        return []
    except Exception as e:
        logger.warning(f"SearXNG error: {e}")
        return []


async def is_searxng_available() -> bool:
    """Quick health check for SearXNG."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_SEARXNG_URL}/healthz",
                timeout=aiohttp.ClientTimeout(total=2),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False


def format_results_for_llm(results: list[dict]) -> str:
    if not results:
        return ""
    lines = ["**Web Search Results:**\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] **{r['title']}**")
        lines.append(f"    {r['snippet']}")
        lines.append(f"    Source: {r['url']}\n")
    return "\n".join(lines)
