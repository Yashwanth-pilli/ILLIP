"""Router classification tiers — small-talk vs brain vs deep."""

import pytest
from app.services import router_service as R


@pytest.mark.parametrize("msg,expected", [
    ("hi", "chat"),
    ("thanks!", "chat"),
    ("how are you?", "chat"),
    ("who are you", "chat"),
    ("lol nice", "chat"),
    ("good morning", "chat"),
    ("tell me a joke", "chat"),
    ("what is 2+2", "simple"),
    ("write a python function to sort a list", "complex"),
    ("hey, build me a complete web scraper app", "complex"),  # work beats greeting
])
def test_classify_tiers(msg, expected):
    assert R._classify(msg) == expected


def test_tiers_map_to_distinct_models():
    # chat -> fast, simple -> brain, complex -> deep (names may vary by install)
    assert R.CHAT and R.SMALL and R.LARGE


@pytest.mark.parametrize("msg,expected", [
    ("grab that file expenses.py", True),
    ("read expenses.py for me", True),
    ("what files are in my workspace", True),
    ("save this to a file", True),
    ("run this python script", True),
    ("open chrome", True),
    ("hi mava", False),
    ("what is 2+2", False),
    ("tell me a joke", False),
    ("explain how photosynthesis works", False),
])
def test_needs_tools(msg, expected):
    # File/system/exec intents must force the real tool loop so the model can't
    # fabricate file contents/paths instead of actually reading them.
    assert R._needs_tools(msg) == expected
