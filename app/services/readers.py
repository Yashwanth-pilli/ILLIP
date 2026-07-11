"""
Keyless multi-source readers — "full internet access" without any API key.

Inspired by agent-reach, but native (no external CLI, no logins for the core
sources). Detects what a URL points at and reads it the smart way:

  YouTube  -> transcript (spoken words), not the HTML shell
  Reddit   -> post body + top comments (via the public .json endpoint)
  GitHub   -> repo README / raw file (public REST, unauthenticated)
  else     -> clean article text via the existing trafilatura page reader

Everything returns the same shape so callers don't care about the source:
    {"source": str, "title": str, "text": str, "url": str, "error": str}

Privacy: readers send ONLY the target URL (and, for YouTube, the video id) to
the public endpoint. No ILLIP memory, chat history, or personal data ever
leaves the machine through here — see privacy note in each fetcher.
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import httpx

from app.utils import logger

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_TIMEOUT = 15


def detect_source(url: str) -> str:
    u = url.lower()
    if "youtube.com/watch" in u or "youtu.be/" in u or "youtube.com/shorts/" in u:
        return "youtube"
    if "reddit.com/" in u:
        return "reddit"
    if "github.com/" in u and "gist.github.com" not in u:
        return "github"
    return "web"


# ── YouTube ───────────────────────────────────────────────────────────────────

def _youtube_id(url: str) -> Optional[str]:
    for pat in (
        r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
    ):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _youtube_transcript_sync(video_id: str) -> str:
    """Fetch transcript with the keyless library. Handles both the old and new
    youtube-transcript-api call styles (the API changed across 0.x -> 1.x)."""
    from youtube_transcript_api import YouTubeTranscriptApi

    def _join(chunks) -> str:
        parts = []
        for c in chunks:
            # dict (old) or object (new) with a .text attribute
            parts.append(c["text"] if isinstance(c, dict) else getattr(c, "text", ""))
        return " ".join(p for p in parts if p).strip()

    # New 1.x instance API
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        return _join(fetched)
    except Exception:
        pass
    # Old classmethod API
    try:
        chunks = YouTubeTranscriptApi.get_transcript(video_id)
        return _join(chunks)
    except Exception as e:
        logger.debug(f"YouTube transcript failed for {video_id}: {e}")
        return ""


async def read_youtube(url: str) -> dict:
    vid = _youtube_id(url)
    if not vid:
        return {"source": "youtube", "title": "", "text": "", "url": url, "error": "no video id"}
    loop = asyncio.get_event_loop()
    # Only the 11-char video id leaves the machine.
    text = await loop.run_in_executor(None, _youtube_transcript_sync, vid)
    if not text:
        # Fall back to reading the page (title/description at least)
        from app.services.browser_service import fetch_page
        page = await fetch_page(url)
        return {"source": "youtube", "title": page.title, "text": page.text,
                "url": url, "error": "" if page.ok else "no transcript, page fallback"}
    return {"source": "youtube", "title": f"YouTube transcript ({vid})", "text": text, "url": url, "error": ""}


# ── Reddit ────────────────────────────────────────────────────────────────────

async def read_reddit(url: str) -> dict:
    # Reddit exposes any post/listing as JSON by appending .json — keyless.
    # www often 403s bots now, so try old.reddit.com too, then fall back to
    # reading the HTML page as an article (still keyless).
    clean = url.split("?")[0].rstrip("/")
    hosts = [clean + ".json",
             clean.replace("://www.reddit.com", "://old.reddit.com").replace("://reddit.com", "://old.reddit.com") + ".json"]
    headers = {"User-Agent": _UA, "Accept": "application/json,text/html;q=0.9"}
    data = None
    for json_url in hosts:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True, headers=headers) as c:
                r = await c.get(json_url)
                if r.status_code == 200:
                    data = r.json()
                    break
        except Exception:
            continue
    if data is None:
        # Last resort: read the page like any article.
        page = await read_web(url)
        page["source"] = "reddit"
        if not page.get("text"):
            page["error"] = "reddit blocked json + page"
        return page

    try:
        post = data[0]["data"]["children"][0]["data"]
        title = post.get("title", "")
        body = post.get("selftext", "") or f"[link post] {post.get('url', '')}"
        lines = [f"# {title}", body, "", "Top comments:"]
        if len(data) > 1:
            for ch in data[1]["data"]["children"][:8]:
                d = ch.get("data", {})
                c_body = d.get("body")
                if c_body:
                    lines.append(f"- ({d.get('score', 0)}▲) {c_body}")
        text = "\n".join(lines).strip()
        return {"source": "reddit", "title": title, "text": text, "url": url, "error": ""}
    except Exception as e:
        return {"source": "reddit", "title": "", "text": "", "url": url, "error": f"parse: {e}"}


# ── GitHub ────────────────────────────────────────────────────────────────────

async def read_github(url: str) -> dict:
    # Public REST, unauthenticated (rate-limited but keyless).
    m = re.search(r"github\.com/([^/]+)/([^/]+)(?:/blob/([^/]+)/(.+))?", url)
    if not m:
        return {"source": "github", "title": "", "text": "", "url": url, "error": "unparseable github url"}
    owner, repo = m.group(1), m.group(2).replace(".git", "")
    branch, path = m.group(3), m.group(4)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True,
                                     headers={"User-Agent": _UA}) as c:
            if path:  # a specific file -> raw content
                raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
                r = await c.get(raw)
                r.raise_for_status()
                return {"source": "github", "title": f"{owner}/{repo}/{path}",
                        "text": r.text[:20000], "url": url, "error": ""}
            # a repo -> README (raw) + description
            r = await c.get(
                f"https://api.github.com/repos/{owner}/{repo}/readme",
                headers={"Accept": "application/vnd.github.raw", "User-Agent": _UA},
            )
            readme = r.text if r.status_code == 200 else ""
            meta = await c.get(f"https://api.github.com/repos/{owner}/{repo}",
                               headers={"Accept": "application/vnd.github+json", "User-Agent": _UA})
            desc = meta.json().get("description", "") if meta.status_code == 200 else ""
            text = (f"{owner}/{repo} — {desc}\n\n{readme}").strip()
            if not text:
                return {"source": "github", "title": f"{owner}/{repo}", "text": "",
                        "url": url, "error": "no readme/description"}
            return {"source": "github", "title": f"{owner}/{repo}", "text": text[:20000], "url": url, "error": ""}
    except Exception as e:
        return {"source": "github", "title": "", "text": "", "url": url, "error": str(e)}


# ── Generic web ───────────────────────────────────────────────────────────────

async def read_web(url: str) -> dict:
    from app.services.browser_service import fetch_page
    page = await fetch_page(url)
    return {"source": "web", "title": page.title, "text": page.text, "url": url,
            "error": "" if page.ok else (page.error or "empty page")}


# ── Dispatcher ────────────────────────────────────────────────────────────────

_READERS = {
    "youtube": read_youtube,
    "reddit": read_reddit,
    "github": read_github,
    "web": read_web,
}


async def smart_read(url: str) -> dict:
    """Read any URL with the best keyless method for its source."""
    if not url or not url.startswith(("http://", "https://")):
        return {"source": "web", "title": "", "text": "", "url": url, "error": "invalid url"}
    reader = _READERS[detect_source(url)]
    try:
        return await reader(url)
    except Exception as e:
        logger.warning(f"smart_read failed for {url}: {e}")
        return {"source": detect_source(url), "title": "", "text": "", "url": url, "error": str(e)}


async def read_many(urls: list[str], max_concurrent: int = 4) -> list:
    """Smart-read many URLs in parallel, returning browser_service.PageResult
    objects so existing callers (the research agent) work unchanged — but each
    URL now uses its best keyless reader (transcript/json/raw), not raw HTML."""
    from app.services.browser_service import PageResult

    sem = asyncio.Semaphore(max_concurrent)

    async def _one(u: str) -> "PageResult":
        async with sem:
            d = await smart_read(u)
        return PageResult(
            url=d.get("url", u),
            title=d.get("title", ""),
            text=d.get("text", ""),
            error=d.get("error", ""),
            fetched_with=d.get("source", "web"),
        )

    return await asyncio.gather(*[_one(u) for u in urls])
