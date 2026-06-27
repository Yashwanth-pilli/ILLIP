"""
Learning data collector — captures approved interactions for future fine-tuning.

Pipeline: observe -> tag -> store -> pattern_detect -> (later) training batch
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from app.config import settings
from app.utils import logger


def _learning_dir() -> Path:
    p = settings.get_data_path() / "learning"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _approved_file() -> Path:
    return _learning_dir() / "approved_examples.jsonl"


def _patterns_file() -> Path:
    return _learning_dir() / "patterns.jsonl"


def save_approved_example(
    user_message: str,
    assistant_response: str,
    source: str = "chat",
    tags: list[str] = None,
) -> str:
    """
    Save a user-approved interaction as a training example.
    Returns the example ID.
    """
    example_id = hashlib.md5(
        f"{user_message}{assistant_response}".encode()
    ).hexdigest()[:12]

    record = {
        "id": example_id,
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "tags": tags or [],
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response},
        ],
    }

    with open(_approved_file(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    logger.info(f"Learning: approved example saved [{example_id}] source={source}")
    return example_id


def save_correction(
    user_message: str,
    bad_response: str,
    corrected_response: str,
) -> str:
    """Save a user correction — high-value training signal."""
    return save_approved_example(
        user_message, corrected_response,
        source="correction",
        tags=["correction", "high_value"],
    )


def record_task_result(
    task_description: str,
    task_result: str,
    success: bool,
) -> None:
    """Record task outcomes for workflow pattern detection."""
    record = {
        "timestamp": datetime.now().isoformat(),
        "type": "task_result",
        "description": task_description,
        "result": task_result[:500],
        "success": success,
    }
    with open(_patterns_file(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def get_approved_count() -> int:
    f = _approved_file()
    if not f.exists():
        return 0
    return sum(1 for _ in f.open(encoding="utf-8"))


def get_approved_examples(limit: int = 100) -> list[dict]:
    f = _approved_file()
    if not f.exists():
        return []
    lines = f.read_text(encoding="utf-8").splitlines()
    return [json.loads(l) for l in lines[-limit:] if l.strip()]
