"""
Learning endpoints — approve examples, view stats, export training batches.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.learning.collector import (
    save_approved_example, save_correction,
    get_approved_count, get_approved_examples,
)
from app.learning.pattern_detector import get_learning_stats, detect_repeated_patterns
from app.learning.swarm import run_pipeline, batch_preparer

router = APIRouter(prefix="/learning", tags=["learning"])


class ApproveRequest(BaseModel):
    user_message: str
    assistant_response: str
    source: str = "chat"
    tags: list[str] = []


class CorrectionRequest(BaseModel):
    user_message: str
    bad_response: str
    corrected_response: str


@router.get("/stats")
async def learning_stats():
    """Learning data statistics."""
    return get_learning_stats()


@router.post("/approve")
async def approve_example(req: ApproveRequest):
    """Mark an interaction as a good training example."""
    example_id = save_approved_example(
        req.user_message, req.assistant_response,
        source=req.source, tags=req.tags,
    )
    return {"id": example_id, "status": "saved"}


@router.post("/correct")
async def submit_correction(req: CorrectionRequest):
    """Submit a correction — high-value training signal."""
    example_id = save_correction(
        req.user_message, req.bad_response, req.corrected_response
    )
    return {"id": example_id, "status": "saved", "type": "correction"}


@router.get("/patterns")
async def get_patterns(min_count: int = 2):
    """Detect repeated query patterns — shows your habits."""
    return {"patterns": detect_repeated_patterns(min_count=min_count)}


@router.get("/examples")
async def list_examples(limit: int = 50):
    """List saved approved examples."""
    return {"examples": get_approved_examples(limit=limit), "total": get_approved_count()}


@router.post("/export-batch")
async def export_training_batch(limit: int = 500):
    """
    Export approved examples as Alpaca-format training batch.
    Run through swarm pipeline first to filter and label.
    """
    raw = get_approved_examples(limit=limit)
    if not raw:
        raise HTTPException(status_code=404, detail="No approved examples yet.")

    verified = []
    for ex in raw:
        result = await run_pipeline(ex)
        if result:
            verified.append(result)

    batch = await batch_preparer(verified)
    return batch
