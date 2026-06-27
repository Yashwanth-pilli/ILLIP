"""
Web search skill — wraps existing search pipeline (SearXNG → Wikipedia → DDG).
"""

from app.skills.base_skill import BaseSKill
from app.services.search_service import web_search, format_search_results


class WebSearchSkill(BaseSKill):
    name = "web_search"
    description = (
        "Search the web for current information: news, prices, recent events, "
        "people, products, or any fact that may have changed recently. "
        "Do NOT use for math — use calculator instead."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Specific search query. Be concise and precise.",
            },
            "max_results": {
                "type": "integer",
                "description": "Max results to return (default 4, max 8).",
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, max_results: int = 4, **_) -> str:
        results = await web_search(query, max_results=min(int(max_results), 8))
        if not results:
            return f"No results found for '{query}'."
        return format_search_results(results)
