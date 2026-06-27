"""
Self-development service — ILLIP improves its own codebase.

Pipeline:
  1. Scan own code for improvement opportunities
  2. Search GitHub for better solutions
  3. Propose changes with diff
  4. Wait for human approval
  5. Apply approved changes + restart

Safety: NEVER applies changes without explicit approval.
All proposals stored in data/proposals/ for review.
"""

import json
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from app.config import settings
from app.utils import logger


def _proposals_dir() -> Path:
    p = settings.get_data_path() / "proposals"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _proposal_path(proposal_id: str) -> Path:
    return _proposals_dir() / f"{proposal_id}.json"


# ── Proposal lifecycle ────────────────────────────────────────────────────────

def create_proposal(
    title: str,
    description: str,
    file_path: str,
    proposed_code: str,
    original_code: str = "",
    source: str = "self_scan",
    risk_level: str = "low",
) -> dict:
    proposal_id = str(uuid.uuid4())[:8]
    proposal = {
        "id": proposal_id,
        "title": title,
        "description": description,
        "file_path": file_path,
        "original_code": original_code,
        "proposed_code": proposed_code,
        "source": source,
        "risk_level": risk_level,
        "status": "pending",          # pending | approved | rejected | applied
        "created_at": datetime.now().isoformat(),
        "applied_at": None,
    }
    _proposal_path(proposal_id).write_text(
        json.dumps(proposal, indent=2), encoding="utf-8"
    )
    logger.info(f"Self-dev proposal created: [{proposal_id}] {title}")
    return proposal


def list_proposals(status: str = None) -> list[dict]:
    proposals = []
    for f in _proposals_dir().glob("*.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            if status is None or p.get("status") == status:
                proposals.append(p)
        except Exception:
            continue
    return sorted(proposals, key=lambda x: x["created_at"], reverse=True)


def get_proposal(proposal_id: str) -> dict | None:
    path = _proposal_path(proposal_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def approve_proposal(proposal_id: str) -> dict:
    p = get_proposal(proposal_id)
    if not p:
        raise ValueError(f"Proposal {proposal_id} not found")
    if p["status"] != "pending":
        raise ValueError(f"Proposal {proposal_id} is already {p['status']}")
    p["status"] = "approved"
    _proposal_path(proposal_id).write_text(json.dumps(p, indent=2), encoding="utf-8")
    return p


def reject_proposal(proposal_id: str) -> dict:
    p = get_proposal(proposal_id)
    if not p:
        raise ValueError(f"Proposal {proposal_id} not found")
    p["status"] = "rejected"
    _proposal_path(proposal_id).write_text(json.dumps(p, indent=2), encoding="utf-8")
    return p


def apply_proposal(proposal_id: str) -> dict:
    """Apply an approved proposal by writing the proposed code to the target file."""
    p = get_proposal(proposal_id)
    if not p:
        raise ValueError(f"Proposal {proposal_id} not found")
    if p["status"] != "approved":
        raise ValueError(f"Proposal {proposal_id} must be approved before applying")

    project_root = settings.project_root
    target = project_root / p["file_path"]

    if not target.exists():
        raise FileNotFoundError(f"Target file not found: {p['file_path']}")

    # Backup original
    backup = target.with_suffix(target.suffix + f".bak.{proposal_id}")
    backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")

    # Apply change
    target.write_text(p["proposed_code"], encoding="utf-8")

    p["status"] = "applied"
    p["applied_at"] = datetime.now().isoformat()
    _proposal_path(proposal_id).write_text(json.dumps(p, indent=2), encoding="utf-8")

    logger.info(f"Self-dev: applied proposal [{proposal_id}] → {p['file_path']}")
    return p


# ── Self-scan: find improvement opportunities in own code ────────────────────

def scan_for_improvements(max_issues: int = 10) -> list[dict]:
    """
    Scan ILLIP's own codebase for common improvement patterns.
    Returns list of {file, issue, suggestion} dicts.
    """
    project_root = settings.project_root
    issues = []

    patterns = [
        # (pattern_str, issue_description, suggestion)
        ("except Exception:", "Bare except catches everything — too broad",
         "Catch specific exceptions (ValueError, IOError, etc.)"),
        ("time.sleep(", "Blocking sleep in async code",
         "Use await asyncio.sleep() instead"),
        ("print(", "Debug print statement in production code",
         "Replace with logger.debug() or logger.info()"),
        ("TODO:", "Unresolved TODO comment",
         "Address or remove TODO before shipping"),
        ("FIXME:", "Known bug marked FIXME",
         "Priority: fix or create proposal"),
        ("hardcoded", "Hardcoded value",
         "Move to config or constant"),
    ]

    app_dir = project_root / "app"
    if not app_dir.exists():
        return []

    for py_file in sorted(app_dir.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        rel_path = str(py_file.relative_to(project_root))
        for i, line in enumerate(lines, 1):
            for pattern, issue, suggestion in patterns:
                if pattern.lower() in line.lower():
                    issues.append({
                        "file": rel_path,
                        "line": i,
                        "code": line.strip(),
                        "issue": issue,
                        "suggestion": suggestion,
                    })
                    if len(issues) >= max_issues:
                        return issues

    return issues


# ── GitHub-based self-improvement ─────────────────────────────────────────────

async def search_and_propose_improvement(topic: str, file_path: str) -> dict | None:
    """
    Search GitHub for better solutions to a topic, create a proposal if found.
    Example: topic="fast pdf text extraction python", file_path="app/skills/builtin/pdf_reader.py"
    """
    try:
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://api.github.com/search/repositories",
                params={"q": topic + " language:python", "sort": "stars", "per_page": 3},
                headers={"Accept": "application/vnd.github+json", "User-Agent": "ILLIP-AI/1.0"},
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        items = data.get("items", [])
        if not items:
            return None

        top = items[0]
        proposal = create_proposal(
            title=f"Consider using {top['full_name']} for {topic}",
            description=(
                f"GitHub search for '{topic}' found: {top['full_name']} "
                f"({top.get('stargazers_count', 0):,} stars)\n"
                f"{top.get('description', '')}\n"
                f"URL: {top.get('html_url', '')}"
            ),
            file_path=file_path,
            proposed_code="",   # human reviews and fills in actual code
            source="github_search",
            risk_level="low",
        )
        return proposal
    except Exception as e:
        logger.debug(f"GitHub proposal search failed: {e}")
        return None


_self_dev_service = None


def get_self_dev_service():
    global _self_dev_service
    if _self_dev_service is None:
        _self_dev_service = type("SelfDevService", (), {
            "create_proposal": staticmethod(create_proposal),
            "list_proposals": staticmethod(list_proposals),
            "get_proposal": staticmethod(get_proposal),
            "approve_proposal": staticmethod(approve_proposal),
            "reject_proposal": staticmethod(reject_proposal),
            "apply_proposal": staticmethod(apply_proposal),
            "scan_for_improvements": staticmethod(scan_for_improvements),
            "search_and_propose": staticmethod(search_and_propose_improvement),
        })()
    return _self_dev_service
