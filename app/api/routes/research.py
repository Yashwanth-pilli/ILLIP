"""
Research API — Perplexity-style deep research with SSE streaming.

POST /api/research        → start research, returns task_id
GET  /api/research/stream → SSE stream of ResearchStep events
GET  /api/research/tasks  → list all agent pool tasks
"""

import asyncio
import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.research_agent import get_research_agent
from app.agents.pool import get_pool
from app.utils import logger

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str
    depth: str = "standard"    # "quick" | "standard" | "deep"


@router.post("")
async def start_research(req: ResearchRequest):
    """Start research and stream via /api/research/stream?query=..."""
    return {"query": req.query, "depth": req.depth, "stream_url": f"/api/research/stream?query={req.query}&depth={req.depth}"}


@router.get("/stream")
async def stream_research(
    query: str = Query(...),
    depth: str = Query("standard"),
):
    """
    SSE endpoint — streams ResearchStep events as they happen.
    Frontend connects with EventSource.

    Event format:
        data: {"type": "search", "message": "...", "data": {...}}
    """
    agent = get_research_agent()

    async def event_generator():
        try:
            async for step in agent.research(query=query, depth=depth):
                yield step.to_sse()
                if step.type in ("done", "error"):
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            err = json.dumps({"type": "error", "message": str(e), "data": {}})
            yield f"data: {err}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ask")
async def ask(req: ResearchRequest):
    """Non-streaming Perplexity-style answer for inline chat use (`/ask`).
    Runs the full research pipeline (keyless search -> read pages -> cited
    synthesis) and returns the final answer + sources in one shot."""
    agent = get_research_agent()
    answer, sources, subs = "", [], []
    try:
        async for step in agent.research(query=req.query, depth=req.depth or "quick"):
            if step.type == "done":
                answer = step.data.get("answer", "")
                sources = step.data.get("sources", [])
                subs = step.data.get("sub_questions", [])
            elif step.type == "error":
                return {"answer": "", "sources": [], "error": step.message}
    except Exception as e:
        logger.error(f"/ask failed: {e}")
        return {"answer": "", "sources": [], "error": str(e)}
    return {"answer": answer, "sources": sources, "sub_questions": subs}


class ReadRequest(BaseModel):
    url: str


@router.post("/read")
async def read_url(req: ReadRequest):
    """Keyless smart-read of any URL — YouTube transcript, Reddit thread,
    GitHub readme/file, or clean article text. No API key."""
    from app.services.readers import smart_read
    d = await smart_read(req.url.strip())
    # Cap payload so a huge page doesn't flood the chat.
    d["text"] = (d.get("text") or "")[:8000]
    return d


@router.get("/tasks")
async def list_tasks():
    """Show all running/recent agent pool tasks."""
    pool = get_pool()
    return {
        "active": pool.active_tasks(),
        "recent": pool.all_tasks(limit=20),
    }


@router.delete("/tasks/clear")
async def clear_done_tasks():
    pool = get_pool()
    cleared = pool.clear_done()
    return {"cleared": cleared}
