"""
Self-development API — ILLIP proposes, scans, and applies improvements to itself.
All destructive actions require explicit human approval.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.self_dev_service import (
    create_proposal, list_proposals, get_proposal,
    approve_proposal, reject_proposal, apply_proposal,
    scan_for_improvements, search_and_propose_improvement,
)

router = APIRouter(prefix="/self-dev", tags=["self-dev"])


class ProposalRequest(BaseModel):
    title: str
    description: str
    file_path: str
    proposed_code: str
    original_code: str = ""
    risk_level: str = "low"


class SearchProposalRequest(BaseModel):
    topic: str
    file_path: str


@router.get("/proposals")
async def list_all_proposals(status: Optional[str] = None):
    """List improvement proposals. Filter by: pending, approved, rejected, applied."""
    return {"proposals": list_proposals(status)}


@router.get("/proposals/{proposal_id}")
async def get_one_proposal(proposal_id: str):
    p = get_proposal(proposal_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return p


@router.post("/proposals")
async def create_new_proposal(req: ProposalRequest):
    """Create a self-improvement proposal for human review."""
    p = create_proposal(
        req.title, req.description, req.file_path,
        req.proposed_code, req.original_code, risk_level=req.risk_level,
    )
    return p


@router.post("/proposals/{proposal_id}/approve")
async def approve(proposal_id: str):
    """Approve a proposal — still needs /apply to actually change code."""
    try:
        return approve_proposal(proposal_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proposals/{proposal_id}/reject")
async def reject(proposal_id: str):
    try:
        return reject_proposal(proposal_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proposals/{proposal_id}/apply")
async def apply(proposal_id: str):
    """Apply an approved proposal. Backs up original file first."""
    try:
        return apply_proposal(proposal_id)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scan")
async def scan_codebase(max_issues: int = 20):
    """Scan ILLIP's own code for improvement opportunities."""
    issues = scan_for_improvements(max_issues)
    return {"issues": issues, "count": len(issues)}


@router.post("/search-and-propose")
async def search_github_propose(req: SearchProposalRequest):
    """Search GitHub for better solutions and auto-create a proposal."""
    result = await search_and_propose_improvement(req.topic, req.file_path)
    if not result:
        raise HTTPException(status_code=404, detail="No GitHub results found.")
    return result
