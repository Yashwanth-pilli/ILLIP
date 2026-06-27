"""
GitHub search skill — find repos, packages, code solutions.
Uses GitHub public API (no token needed for basic search, 60 req/hr).
"""

import aiohttp
from app.skills.base_skill import BaseSKill
from app.utils import logger


class GitHubSearchSkill(BaseSKill):
    name = "github_search"
    description = (
        "Search GitHub for repositories, libraries, tools, or code examples. "
        "Use when looking for open-source packages, solutions, or how others solved a problem."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query (e.g. 'fastapi jwt auth', 'python pdf reader')"},
            "language": {"type": "string", "description": "Filter by language (e.g. 'python', 'javascript'). Optional."},
            "max_results": {"type": "integer", "description": "Max repos to return (default 5, max 10)"},
        },
        "required": ["query"],
    }

    async def execute(self, query: str, language: str = None, max_results: int = 5, **_) -> str:
        q = query.strip()
        if language:
            q += f" language:{language}"

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    "https://api.github.com/search/repositories",
                    params={"q": q, "sort": "stars", "order": "desc", "per_page": min(max_results, 10)},
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "ILLIP-AI/1.0"},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status == 403:
                        return "GitHub rate limit hit. Wait 1 minute and try again."
                    if resp.status != 200:
                        return f"GitHub search failed: HTTP {resp.status}"
                    data = await resp.json()

            items = data.get("items", [])
            if not items:
                return f"No repos found for '{query}'."

            lines = [f"GitHub repos for '{query}':\n"]
            for r in items:
                stars = r.get("stargazers_count", 0)
                desc  = (r.get("description") or "No description")[:100]
                lang  = r.get("language") or "unknown"
                url   = r.get("html_url", "")
                lines.append(f"[{stars:,}★ {lang}] {r['full_name']}")
                lines.append(f"  {desc}")
                lines.append(f"  {url}\n")

            return "\n".join(lines)

        except aiohttp.ClientConnectorError:
            return "Cannot reach GitHub. Check internet connection."
        except Exception as e:
            logger.debug(f"GitHub search failed: {e}")
            return f"GitHub search error: {e}"
