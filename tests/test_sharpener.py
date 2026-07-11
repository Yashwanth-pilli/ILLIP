"""
Tests for the Sharpener — ILLIP's brain-agnostic answer-lift loop.

The loop is model-independent, so these tests inject a scripted fake brain
(no Ollama needed) and assert the loop behaves: lifts when the critique finds
a flaw, stops clean when it doesn't, and never worsens the draft.
"""

import pytest

from app.services import sharpener
from app.services.sharpener import sharpen, critique_is_clean, SharpenResult


# ── pure helper: critique_is_clean ────────────────────────────────────────────

@pytest.mark.parametrize("critique,expected_clean", [
    ("NONE", True),
    ("none", True),
    ("  NONE.  ", True),
    ("no issues", True),
    ("", True),
    ("   ", True),
    ("- The date is wrong, 1969 not 1970", False),
    ("- missing base case\n- off-by-one in loop", False),
    ("* unsupported claim about GDP", False),
])
def test_critique_is_clean(critique, expected_clean):
    assert critique_is_clean(critique) is expected_clean


# ── fake brain ────────────────────────────────────────────────────────────────

class _FakeLLM:
    """Scripted provider-agnostic client. Routes by the system prompt so we can
    give distinct draft / critique / refine replies."""
    def __init__(self, draft, critique, refined):
        self._draft, self._critique, self._refined = draft, critique, refined
        self.calls = []

    async def complete(self, prompt, system=None):
        self.calls.append(system)
        if system == sharpener._CRITIQUE_SYS:
            return self._critique
        if system == sharpener._REFINE_SYS:
            return self._refined
        return self._draft


@pytest.fixture
def patch_llm(monkeypatch):
    def _install(draft, critique, refined):
        fake = _FakeLLM(draft, critique, refined)
        monkeypatch.setattr(sharpener, "get_llm", lambda: fake)
        return fake
    return _install


# ── behavior ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sharpen_lifts_when_critique_finds_flaw(patch_llm):
    fake = patch_llm(
        draft="The moon landing was in 1970.",
        critique="- Wrong date: it was 1969, not 1970.",
        refined="The moon landing was in 1969.",
    )
    res = await sharpen("When was the moon landing?", ground=False)
    assert isinstance(res, SharpenResult)
    assert res.draft == "The moon landing was in 1970."
    assert res.answer == "The moon landing was in 1969."
    assert res.improved is True
    assert res.rounds_run == 1
    # draft -> critique -> refine = 3 model calls
    assert len(fake.calls) == 3


@pytest.mark.asyncio
async def test_sharpen_stops_clean_no_change(patch_llm):
    patch_llm(
        draft="Water boils at 100 C at sea level.",
        critique="NONE",
        refined="(should never be used)",
    )
    res = await sharpen("At what temperature does water boil?", ground=False)
    assert res.answer == res.draft
    assert res.improved is False
    assert res.rounds_run == 1  # one critique round, recorded, no refine


@pytest.mark.asyncio
async def test_sharpen_never_worsens_on_draft_error(patch_llm):
    patch_llm(draft="Error: provider not available", critique="x", refined="y")
    res = await sharpen("anything", ground=False)
    assert res.answer.startswith("Error")
    assert res.rounds_run == 0
    assert res.improved is False


@pytest.mark.asyncio
async def test_sharpen_keeps_prior_when_refine_empty(patch_llm):
    # Reviewer flags a problem but the refine step returns nothing usable —
    # the loop must keep the draft, not blank it out.
    patch_llm(draft="A solid draft answer.", critique="- too short", refined="")
    res = await sharpen("q", ground=False)
    assert res.answer == "A solid draft answer."
    assert res.improved is False


@pytest.mark.asyncio
async def test_sharpen_multi_round_capped(patch_llm):
    # Critique always complains; loop must stop when refine stops changing text.
    fake = patch_llm(draft="v1", critique="- fix it", refined="v1")  # refine == draft
    res = await sharpen("q", ground=False, rounds=3)
    # refine returns same text -> changed False -> break after first round
    assert res.rounds_run == 1
    assert res.answer == "v1"


@pytest.mark.asyncio
async def test_sharpen_route_registered(test_client):
    # Endpoint exists and validates empty input (no real model call).
    r = test_client.post("/api/chat/sharpen", json={"message": "   "})
    assert r.status_code == 400
