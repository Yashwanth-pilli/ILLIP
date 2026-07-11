"""Pure-logic tests for keyless readers + skills directory (no network)."""

import pytest

from app.services.readers import detect_source, _youtube_id
from app.services import skills_catalog


@pytest.mark.parametrize("url,src", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
    ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
    ("https://www.youtube.com/shorts/abcdefghijk", "youtube"),
    ("https://www.reddit.com/r/python/comments/x/y/", "reddit"),
    ("https://github.com/VoltAgent/awesome-agent-skills", "github"),
    ("https://en.wikipedia.org/wiki/Python", "web"),
    ("https://example.com/some/article", "web"),
])
def test_detect_source(url, src):
    assert detect_source(url) == src


@pytest.mark.parametrize("url,vid", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/abcdefghijk", "abcdefghijk"),
    ("https://example.com/nope", None),
])
def test_youtube_id(url, vid):
    assert _youtube_id(url) == vid


def test_directory_lists_and_filters():
    d = skills_catalog.directory()
    assert d["count"] > 20
    assert "web" in d["categories"]
    assert d["source"].startswith("https://github.com/VoltAgent")
    # Every entry has the fields the UI needs
    for s in d["skills"]:
        assert s["name"] and s["category"] and s["description"] and s["id"] and s["url"]


def test_directory_category_filter():
    d = skills_catalog.directory(category="security")
    assert d["count"] >= 1
    assert all(s["category"] == "security" for s in d["skills"])


def test_directory_query_search():
    d = skills_catalog.directory(query="playwright")
    assert d["count"] >= 1
    assert all("playwright" in (s["name"] + s["description"]).lower() for s in d["skills"])
