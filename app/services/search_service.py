"""
Search service — free, no API key, works from India.

Pipeline:
  1. Local SearXNG   — if running via Docker (best, most comprehensive)
  2. DDG Instant Answer API — free factual answers, no key
  3. Wikipedia Search — free, authoritative, global
  4. LLM fallback    — answers from training knowledge

To enable full web search (best option, one command):
  docker run -d -p 8888:8080 --name searxng searxng/searxng
"""

import asyncio
import re
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx
from app.utils import logger


async def _local_searxng(query: str, max_results: int) -> List[Dict[str, str]]:
    """Local SearXNG — fastest, most comprehensive. Needs Docker."""
    from app.config import settings
    url = getattr(settings, "searxng_url", "http://localhost:8888")
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.get(
                f"{url}/search",
                params={"q": query, "format": "json", "categories": "general"},
                headers={"Accept": "application/json"},
            )
            if r.status_code == 200:
                data = r.json()
                results = [
                    {"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("content", "")}
                    for x in data.get("results", [])[:max_results]
                    if x.get("title")
                ]
                if results:
                    logger.info(f"Local SearXNG: {len(results)} results")
                    return results
    except Exception:
        pass
    return []


async def _ddg_instant(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    DuckDuckGo Instant Answer API — free, no key, works globally.
    Returns factual answers, definitions, related topics.
    """
    try:
        async with httpx.AsyncClient(timeout=6, follow_redirects=True) as client:
            r = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                headers={"User-Agent": "ILLIP-AI/3.1"},
            )
            if r.status_code != 200:
                return []

            data = r.json()
            results = []

            # Abstract (main answer)
            if data.get("Abstract") and data.get("AbstractURL"):
                results.append({
                    "title":   data.get("Heading", query),
                    "url":     data.get("AbstractURL", ""),
                    "snippet": data.get("Abstract", ""),
                })

            # Related topics
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                    results.append({
                        "title":   topic.get("Text", "")[:80],
                        "url":     topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                    })
                if len(results) >= max_results:
                    break

            if results:
                logger.info(f"DDG Instant: {len(results)} results")
            return results[:max_results]
    except Exception as e:
        logger.debug(f"DDG instant failed: {e}")
        return []


async def _wikipedia_search(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    Wikipedia Search API — free, authoritative, works globally.
    Good for factual, scientific, historical, technical topics.
    """
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            # Search for pages
            search_r = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": max_results,
                    "format": "json",
                    "utf8": "1",
                },
                headers={"User-Agent": "ILLIP-AI/3.1 (local assistant)"},
            )
            if search_r.status_code != 200:
                return []

            pages = search_r.json().get("query", {}).get("search", [])
            if not pages:
                return []

            results = []
            for p in pages[:max_results]:
                title = p.get("title", "")
                snippet = re.sub(r'<[^>]+>', '', p.get("snippet", ""))  # strip HTML
                url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                results.append({"title": title, "url": url, "snippet": snippet})

            if results:
                logger.info(f"Wikipedia: {len(results)} results")
            return results
    except Exception as e:
        logger.debug(f"Wikipedia search failed: {e}")
        return []


async def _ddg_full_search(query: str, max_results: int) -> List[Dict[str, str]]:
    """DuckDuckGo full web search — no API key, works globally."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        loop = asyncio.get_event_loop()
        def _run():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            items = await loop.run_in_executor(None, _run)
        results = [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in items if r.get("title")
        ]
        if results:
            logger.info(f"DDG full search: {len(results)} results for '{query}'")
        return results
    except Exception as e:
        logger.debug(f"DDG full search failed: {e}")
        return []


async def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Free search — no API key, works globally.
    Priority: SearXNG (Docker) → DDG full search → Wikipedia + DDG instant
    """
    # 1. Local SearXNG (best — run: docker run -d -p 8888:8080 searxng/searxng)
    results = await _local_searxng(query, max_results)
    if results:
        return results

    # 2. DDG full web search (installed library, no API key needed)
    results = await _ddg_full_search(query, max_results)
    if results:
        return results

    # 3. Wikipedia + DDG instant fallback
    wiki_task = asyncio.create_task(_wikipedia_search(query, max_results))
    ddg_task  = asyncio.create_task(_ddg_instant(query, max_results))
    wiki_res, ddg_res = await asyncio.gather(wiki_task, ddg_task)

    seen_urls = {r["url"] for r in wiki_res}
    merged = list(wiki_res)
    for r in ddg_res:
        if r["url"] not in seen_urls and len(merged) < max_results:
            merged.append(r)
            seen_urls.add(r["url"])

    if merged:
        return merged[:max_results]

    logger.info(f"All search providers failed: '{query}'")
    return []


def format_search_results(results: List[Dict[str, str]]) -> str:
    if not results:
        return "No search results found."
    lines = ["**Search Results:**\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   {r['snippet']}")
        lines.append(f"   Source: {r['url']}\n")
    return "\n".join(lines)


async def search_and_summarize(query: str, max_results: int = 5) -> Dict[str, Any]:
    results = await web_search(query, max_results=max_results)
    context = format_search_results(results)
    return {"query": query, "results": results, "context": context, "count": len(results)}


_search_service: Optional["SearchService"] = None


class SearchService:
    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        return await search_and_summarize(query, max_results)


def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
