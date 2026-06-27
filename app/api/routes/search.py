"""
Search endpoints — web search with optional LLM synthesis (Perplexity-style).
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.search_service import get_search_service
from app.services.chat_service import get_chat_service
from app.core import Message
from app.providers import get_provider
from app.utils import logger, get_current_timestamp

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def search(
    q: str = Query(..., description="Search query"),
    max_results: int = Query(5, ge=1, le=10),
    synthesize: bool = Query(False, description="Use LLM to synthesize results into an answer"),
):
    """
    Web search. With synthesize=true, LLM reads results and writes a cited answer.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        search_service = get_search_service()
        data = await search_service.search(q.strip(), max_results=max_results)

        provider = await get_provider()

        # No web results — answer from LLM knowledge
        if not data["results"]:
            messages = [
                Message(
                    role="system",
                    content=(
                        "You are ILLIP. Web search is not available right now. "
                        "Answer concisely from your training knowledge. "
                        "Start your answer directly. Do not explain the lack of search. "
                        "If you don't know, say 'I don't have current information on this.'"
                    ),
                    timestamp=get_current_timestamp(),
                ),
                Message(role="user", content=q, timestamp=get_current_timestamp()),
            ]
            answer = await provider.safe_generate(messages=messages, temperature=0.2)
            return {
                **data,
                "synthesized_answer": answer,
                "web_search_available": False,
            }

        if not synthesize:
            return data

        # Perplexity-style: inject search results into LLM context
        messages = [
            Message(
                role="system",
                content=(
                    "You are ILLIP, a research assistant. "
                    "Synthesize the search results into a clear, accurate answer. "
                    "Cite sources using [1], [2], etc. List sources at the end."
                ),
                timestamp=get_current_timestamp(),
            ),
            Message(
                role="user",
                content=(
                    f"Question: {q}\n\n"
                    f"{data['context']}\n\n"
                    "Synthesize these results into a clear answer with citations."
                ),
                timestamp=get_current_timestamp(),
            ),
        ]
        answer = await provider.safe_generate(messages=messages, temperature=0.3)
        return {**data, "synthesized_answer": answer}

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
