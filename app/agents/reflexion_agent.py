"""
Hermes-style reflexion agent — evaluate own output, retry if poor, evolve system prompt.

Flow:
  1. Model generates response
  2. Reflexion evaluates quality (1-10) using small fast model
  3. If score < threshold: retry with improved prompt
  4. Store what worked; periodically distill into system prompt update proposals

Self-prompt evolution:
  - After N successful high-quality responses, extract patterns
  - Create self-dev proposal to update system_prompt.md
  - Human approves/rejects like any other proposal
"""

import json
import re
from pathlib import Path
from app.utils import logger
from app.config import settings

_EVAL_MODEL = "qwen2.5:3b"      # fast cheap evaluator
_QUALITY_THRESHOLD = 6           # retry if score < this
_MAX_RETRIES = 2
_PATTERN_FILE = Path("data/learning/reflexion_patterns.jsonl")


_EVAL_PROMPT = """You are a strict quality evaluator. Rate this AI response 1-10.

Criteria:
- Accuracy: is the answer factually correct?
- Helpfulness: does it fully address the question?
- Conciseness: no padding, no repetition?
- Tone: professional, not sycophantic?

Penalize heavily: "as an AI", "I cannot", filler phrases, hedging without reason.
Reward: direct answers, code that runs, specific facts.

Question: {question}
Response: {response}

Reply ONLY with JSON: {{"score": <1-10>, "reason": "<one line>"}}"""


_RETRY_SYSTEM_ADDITION = """
RETRY INSTRUCTION: Your previous response scored {score}/10.
Reason: {reason}
Fix this specifically. Be more direct, more accurate, less verbose.
"""


async def evaluate_response(question: str, response: str, base_url: str = "http://localhost:11434") -> tuple[int, str]:
    """
    Score a response 1-10. Returns (score, reason).
    Falls back to (7, "eval unavailable") on error.
    """
    try:
        import aiohttp
        prompt = _EVAL_PROMPT.format(question=question[:500], response=response[:1000])
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{base_url}/api/generate",
                json={
                    "model": _EVAL_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_ctx": 2048},
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    return 7, "eval unavailable"
                data = await resp.json()
                text = data.get("response", "")

        m = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if m:
            parsed = json.loads(m.group())
            score = int(parsed.get("score", 7))
            reason = str(parsed.get("reason", ""))
            return max(1, min(10, score)), reason
    except Exception as e:
        logger.debug(f"Reflexion eval error: {e}")
    return 7, "eval unavailable"


def _save_pattern(question: str, response: str, score: int, retry: bool) -> None:
    """Log high-quality examples for pattern extraction."""
    if score < 8:
        return
    _PATTERN_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {"q": question[:300], "a": response[:800], "score": score, "was_retry": retry}
    with _PATTERN_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


async def reflexion_wrap(
    question: str,
    generate_fn,          # async callable(system_suffix: str) -> str
    base_url: str = "http://localhost:11434",
) -> tuple[str, int, bool]:
    """
    Wrap any generation call with reflexion.
    generate_fn receives an optional system suffix for retry instructions.

    Returns (final_response, final_score, was_retried).
    """
    response = await generate_fn("")
    score, reason = await evaluate_response(question, response, base_url)
    logger.info(f"Reflexion: score={score}/10 reason={reason!r}")

    retried = False
    for attempt in range(_MAX_RETRIES):
        if score >= _QUALITY_THRESHOLD:
            break
        logger.info(f"Reflexion: retrying (attempt {attempt+1}, score={score})")
        suffix = _RETRY_SYSTEM_ADDITION.format(score=score, reason=reason)
        response = await generate_fn(suffix)
        new_score, new_reason = await evaluate_response(question, response, base_url)
        logger.info(f"Reflexion: retry score={new_score}/10 reason={new_reason!r}")
        if new_score > score:
            score, reason = new_score, new_reason
            retried = True
        else:
            break   # getting worse, stop

    _save_pattern(question, response, score, retried)
    return response, score, retried


async def propose_system_prompt_update(min_patterns: int = 20) -> dict | None:
    """
    Periodically called by autonomy daemon.
    If enough high-quality patterns collected, propose system prompt update.
    """
    if not _PATTERN_FILE.exists():
        return None

    lines = _PATTERN_FILE.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) < min_patterns:
        return None

    patterns = [json.loads(l) for l in lines[-min_patterns:]]
    avg_score = sum(p["score"] for p in patterns) / len(patterns)
    if avg_score < 8.5:
        return None

    # Distill: what did the high-scoring answers have in common?
    # Simple heuristic: check for common patterns in answers
    direct_count = sum(1 for p in patterns if not p["a"].startswith("As an AI"))
    code_count = sum(1 for p in patterns if "```" in p["a"])

    note = f"Based on {len(patterns)} high-quality examples (avg score {avg_score:.1f}/10). "
    note += f"{direct_count}/{len(patterns)} gave direct answers. "
    note += f"{code_count}/{len(patterns)} included code."

    # Create self-dev proposal to update system prompt
    from app.services.self_dev_service import create_proposal
    proposal = create_proposal(
        title="Reflexion: system prompt refinement",
        description=note,
        file_path="app/prompts/system_prompt.md",
        proposed_code="",   # human reviews and edits actual prompt
        source="reflexion_agent",
        risk_level="low",
    )
    logger.info(f"Reflexion: created system prompt proposal {proposal['id']}")
    return proposal
