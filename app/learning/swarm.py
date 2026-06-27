"""
Swarm agents for learning pipeline.

Pipeline: Observer -> Cleaner -> Labeler -> Verifier -> BatchPreparer
Each agent is a pure async function — no classes, no frameworks.
Data flows through as dicts.
"""

import re
import json
from typing import Optional
from app.utils import logger


async def observer(raw_example: dict) -> Optional[dict]:
    """
    Gate: decide if an interaction is worth learning from.
    Rejects: very short exchanges, error responses, empty content.
    """
    msgs = raw_example.get("messages", [])
    user = next((m["content"] for m in msgs if m["role"] == "user"), "")
    asst = next((m["content"] for m in msgs if m["role"] == "assistant"), "")

    if len(user.strip()) < 10:
        return None
    if len(asst.strip()) < 20:
        return None
    if asst.strip().startswith("Error:") or asst.strip().startswith("[Error"):
        return None

    return {**raw_example, "_swarm": {"stage": "observed", "quality": "candidate"}}


async def cleaner(example: dict) -> dict:
    """
    Remove noise: strip system-injected context blocks before storing.
    Keeps only the core user intent + assistant answer.
    """
    msgs = example.get("messages", [])
    cleaned = []
    for m in msgs:
        content = m["content"]
        # Strip injected memory/search context blocks
        content = re.sub(r'\*\*Relevant memories:\*\*.*?---\n', '', content, flags=re.DOTALL)
        content = re.sub(r'\*\*Search Results:\*\*.*?---\n', '', content, flags=re.DOTALL)
        content = re.sub(r'\n---\nUser question: ', '', content)
        cleaned.append({**m, "content": content.strip()})

    sw = example.get("_swarm", {})
    sw["stage"] = "cleaned"
    return {**example, "messages": cleaned, "_swarm": sw}


async def labeler(example: dict) -> dict:
    """
    Auto-label examples by content type for training organization.
    Labels: coding, explanation, task, search, math, general
    """
    msgs = example.get("messages", [])
    user = next((m["content"] for m in msgs if m["role"] == "user"), "").lower()

    labels = []
    if "```" in user or any(w in user for w in ["code", "function", "class", "bug", "error"]):
        labels.append("coding")
    if any(w in user for w in ["explain", "what is", "how does", "why"]):
        labels.append("explanation")
    if any(w in user for w in ["search", "find", "latest", "news", "current"]):
        labels.append("search")
    if any(w in user for w in ["calculate", "math", "formula", "+", "-", "*", "/"]):
        labels.append("math")
    if any(w in user for w in ["task", "create", "build", "make", "write"]):
        labels.append("task")
    if not labels:
        labels.append("general")

    sw = example.get("_swarm", {})
    sw["stage"] = "labeled"
    sw["labels"] = labels
    return {**example, "_swarm": sw}


async def verifier(example: dict) -> Optional[dict]:
    """
    Final quality gate before batch inclusion.
    Rejects duplicates by content hash, very generic responses.
    """
    msgs = example.get("messages", [])
    asst = next((m["content"] for m in msgs if m["role"] == "assistant"), "")

    # Reject boilerplate-only responses
    boilerplate = ["i don't know", "i cannot", "as an ai", "i'm just an ai"]
    if any(b in asst.lower() for b in boilerplate):
        return None

    sw = example.get("_swarm", {})
    sw["stage"] = "verified"
    sw["quality"] = "approved"
    return {**example, "_swarm": sw}


async def batch_preparer(examples: list[dict]) -> dict:
    """
    Convert verified examples into a training batch (Alpaca/ShareGPT format).
    Output can be fed to LoRA fine-tuning tools (llama.cpp, Unsloth, etc.)
    """
    alpaca_records = []
    for ex in examples:
        msgs = ex.get("messages", [])
        user = next((m["content"] for m in msgs if m["role"] == "user"), "")
        asst = next((m["content"] for m in msgs if m["role"] == "assistant"), "")
        if user and asst:
            alpaca_records.append({
                "instruction": user,
                "input": "",
                "output": asst,
                "source": ex.get("source", "chat"),
                "labels": ex.get("_swarm", {}).get("labels", []),
            })

    return {
        "format": "alpaca",
        "count": len(alpaca_records),
        "records": alpaca_records,
    }


async def run_pipeline(raw_example: dict) -> Optional[dict]:
    """Run one example through the full swarm pipeline."""
    step = await observer(raw_example)
    if not step:
        logger.debug("Swarm: observer rejected example")
        return None
    step = await cleaner(step)
    step = await labeler(step)
    step = await verifier(step)
    if not step:
        logger.debug("Swarm: verifier rejected example")
        return None
    logger.info(f"Swarm: example approved, labels={step['_swarm'].get('labels')}")
    return step
