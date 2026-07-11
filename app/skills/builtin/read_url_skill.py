"""
Read-URL skill — gives the agent crew keyless internet reach: fetch and read
any link the smart way (YouTube transcript, GitHub readme/file, article text).
"""

from app.skills.base_skill import BaseSKill
from app.services.readers import smart_read


class ReadUrlSkill(BaseSKill):
    name = "read_url"
    description = (
        "Read the actual content behind a URL. YouTube links return the video "
        "transcript, GitHub links return the readme or file, other links return "
        "the clean article text. Use this after web_search to read a promising "
        "result, or whenever the user gives you a link."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The full http(s) URL to read."},
        },
        "required": ["url"],
    }

    async def execute(self, url: str, **_) -> str:
        d = await smart_read(url.strip())
        if d.get("error") and not d.get("text"):
            return f"Couldn't read {url}: {d['error']}"
        title = d.get("title") or d.get("url")
        text = (d.get("text") or "")[:6000]
        return f"[{d.get('source')}] {title}\n\n{text}"
