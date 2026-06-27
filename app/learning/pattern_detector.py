"""
Pattern detector — finds repeated queries and workflows to surface as learnable habits.
"""

import json
import re
from collections import Counter
from pathlib import Path
from app.config import settings


def _approved_file() -> Path:
    return settings.get_data_path() / "learning" / "approved_examples.jsonl"


def _normalize(text: str) -> str:
    """Strip specifics, keep intent skeleton for similarity grouping."""
    text = text.lower().strip()
    text = re.sub(r'\b\d+\b', 'NUM', text)           # numbers -> NUM
    text = re.sub(r'https?://\S+', 'URL', text)       # URLs -> URL
    text = re.sub(r'`[^`]+`', 'CODE', text)           # inline code -> CODE
    text = re.sub(r'\s+', ' ', text)
    return text[:120]


def detect_repeated_patterns(min_count: int = 2) -> list[dict]:
    """
    Find user message patterns that appear multiple times.
    Returns ranked list of {pattern, count, examples}.
    """
    f = _approved_file()
    if not f.exists():
        return []

    bucket: dict[str, list[str]] = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            msgs = rec.get("messages", [])
            user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
            if not user_msg:
                continue
            key = _normalize(user_msg)
            bucket.setdefault(key, []).append(user_msg)
        except Exception:
            continue

    patterns = [
        {"pattern": k, "count": len(v), "examples": v[:3]}
        for k, v in bucket.items()
        if len(v) >= min_count
    ]
    return sorted(patterns, key=lambda x: x["count"], reverse=True)


def get_learning_stats() -> dict:
    f = _approved_file()
    count = 0
    sources: Counter = Counter()
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                count += 1
                sources[rec.get("source", "unknown")] += 1
            except Exception:
                continue

    patterns = detect_repeated_patterns()
    return {
        "approved_examples": count,
        "sources": dict(sources),
        "repeated_patterns": len(patterns),
        "top_patterns": patterns[:5],
    }
