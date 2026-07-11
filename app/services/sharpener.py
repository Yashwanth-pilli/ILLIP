"""
Sharpener — model-agnostic answer-quality lift at inference time.

This is ILLIP's "not a wrapper" core. It does NOT depend on which brain is
infused (ollama / anthropic / groq / openai-compat / llamafile — anything that
implements BaseProvider). It takes whatever model is active and makes its answer
sharper through a draft -> self-critique -> refine loop, grounded in ILLIP memory.

The value lives here, in the loop — not in the model. Swap the brain, keep the lift.

Pipeline (each stage is one provider call):
  1. recall   — pull relevant ILLIP memory for the question (grounding).
  2. draft    — model answers normally.
  3. critique — SAME model hunts concrete flaws (wrong facts, gaps, bad logic,
                unclear bits). Structured; emits "NONE" when the draft is solid.
  4. refine   — model rewrites, fixing exactly the flaws it found.
  Repeat critique+refine for `rounds` cycles, or stop early when critique = NONE.

Every stage falls back to the last good answer on error, so the Sharpener can
never make a reply worse than a plain call — worst case it equals the draft.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

from app.services.chat_service import get_llm
from app.utils import logger

# Keep prompts short — long prompts hurt TTFT and defocus small (9B) models.
# Conservative on purpose. A self-critique loop around an already-strong model
# tends to OVER-EDIT: it "fixes" a correct answer into a plausible-but-wrong one
# (measured: a refine pass once deleted a correct SQL DISTINCT). So the reviewer
# must flag ONLY definite errors and stay silent when unsure — a false alarm here
# costs a real regression. This is the difference between lifting a weak brain and
# damaging a strong one.
_CRITIQUE_SYS = (
    "You are a careful reviewer. You are given a QUESTION and a draft ANSWER. "
    "Flag ONLY definite, concrete errors: a wrong fact, broken logic, a missing "
    "required step, or an unsafe instruction. Do NOT flag style, tone, or things you "
    "are merely unsure about — when in doubt, do not flag it. Never suggest removing "
    "content that is correct. Do NOT rewrite the answer. Do NOT praise. List each real "
    "error as one short bullet starting with '- '. If the answer is correct and "
    "complete, reply with exactly: NONE"
)

_REFINE_SYS = (
    "You improve an answer using a reviewer's list of errors. Fix ONLY the listed "
    "errors. Keep every other part of the answer exactly as it was — do not reword, "
    "trim, or drop anything that was already correct. Do not add filler or mention the "
    "review. Output only the improved answer."
)

# critique text that means "draft is fine, stop" (checked case-insensitively)
_OK_MARKERS = ("none", "no issues", "no problems", "looks good", "n/a")


@dataclass
class SharpenRound:
    critique: str
    changed: bool


@dataclass
class SharpenResult:
    question: str
    answer: str                       # final, sharpened
    draft: str                        # first-pass, un-sharpened (for A/B + benchmark)
    rounds_run: int
    improved: bool                    # answer differs from draft
    grounded: bool                    # memory context was injected
    provider: str
    history: list = field(default_factory=list)  # list[SharpenRound]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["history"] = [asdict(h) for h in self.history]
        return d


def critique_is_clean(critique: str) -> bool:
    """Pure helper (unit-testable): does the critique say the draft is fine?

    True  -> reviewer found nothing, stop the loop.
    False -> reviewer listed at least one problem, run a refine pass.
    """
    if not critique or not critique.strip():
        return True  # empty critique = nothing to fix
    text = critique.strip().lower()
    # A bare OK marker (whole reply is basically "NONE") = clean.
    stripped = text.strip(" .!-\n\t*")
    if stripped in _OK_MARKERS:
        return True
    # Reviewer that produced no bullet points and is short = treat as clean.
    has_bullets = any(line.strip().startswith(("-", "*", "•")) for line in text.splitlines())
    if not has_bullets and len(stripped) < 40:
        return True
    return False


async def _recall(question: str, project_id: str) -> str:
    """Pull grounding context from ILLIP memory. Never raises."""
    try:
        from app.services.memory_qdrant import retrieve_memory, format_memories_for_prompt
        mems = await retrieve_memory(question, top_k=4, project_id=project_id)
        return format_memories_for_prompt(mems)
    except Exception as e:
        logger.debug(f"Sharpener recall skipped: {e}")
        return ""


async def sharpen(
    question: str,
    *,
    rounds: int = 1,
    ground: bool = True,
    project_id: str = "default",
    system: Optional[str] = None,
) -> SharpenResult:
    """Answer `question` with the active brain, then lift the answer.

    rounds  — max critique+refine cycles (each is 2 model calls). 1 is usually enough.
    ground  — inject ILLIP memory recall into the draft for grounding.
    system  — optional extra system instruction for the draft (persona, mode).

    Returns a SharpenResult carrying BOTH the raw draft and the sharpened answer,
    so callers (and the benchmark) can measure exactly what the loop added.
    """
    llm = get_llm()
    provider_name = ""
    try:
        from app.providers import get_provider
        provider_name = (await get_provider()).name
    except Exception:
        pass

    # 1. recall (grounding)
    context = await _recall(question, project_id) if ground else ""
    grounded = bool(context)

    # 2. draft
    draft_prompt = question if not context else f"{context}\n\nQuestion: {question}"
    draft = await llm.complete(draft_prompt, system=system)
    draft = (draft or "").strip()

    answer = draft
    history: list[SharpenRound] = []

    # If the draft itself failed, don't try to sharpen an error string.
    if not answer or answer.lower().startswith("error"):
        return SharpenResult(
            question=question, answer=answer, draft=draft, rounds_run=0,
            improved=False, grounded=grounded, provider=provider_name, history=history,
        )

    # 3+4. critique -> refine, up to `rounds` times, stop early when clean
    for i in range(max(1, rounds)):
        critique = await llm.complete(
            f"QUESTION:\n{question}\n\nANSWER:\n{answer}",
            system=_CRITIQUE_SYS,
        )
        critique = (critique or "").strip()

        if critique_is_clean(critique):
            history.append(SharpenRound(critique=critique or "NONE", changed=False))
            break

        refined = await llm.complete(
            f"QUESTION:\n{question}\n\nCURRENT ANSWER:\n{answer}\n\n"
            f"REVIEWER FOUND THESE PROBLEMS:\n{critique}\n\n"
            f"Rewrite the answer fixing every problem.",
            system=_REFINE_SYS,
        )
        refined = (refined or "").strip()

        # Guard: never accept an empty/error refine — keep the prior answer.
        changed = bool(refined) and not refined.lower().startswith("error") and refined != answer
        if changed:
            answer = refined
        history.append(SharpenRound(critique=critique, changed=changed))
        if not changed:
            break  # refine added nothing — stop burning tokens

    return SharpenResult(
        question=question,
        answer=answer,
        draft=draft,
        rounds_run=len(history),
        improved=(answer.strip() != draft.strip()),
        grounded=grounded,
        provider=provider_name,
        history=history,
    )
