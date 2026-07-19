"""Regression tests for Telegram bridge auth.

Two past bugs:
1. Empty allowlist meant _is_allowed returned True for everyone — a stranger
   could run commands (incl. /run) before the owner's first /start.
2. _save_owner wrote the owner file sorted, so /allow-ing a numerically
   smaller Telegram ID silently transferred ownership (owner = first line).
"""

from app.connectors import telegram_bot as tb


def test_unclaimed_bot_denies_everyone(monkeypatch):
    monkeypatch.setattr(tb, "_allowed_users", set())
    assert tb._is_allowed(12345) is False


def test_allowlist_enforced(monkeypatch):
    monkeypatch.setattr(tb, "_allowed_users", {111})
    assert tb._is_allowed(111) is True
    assert tb._is_allowed(222) is False


def test_owner_stays_first_line(tmp_path, monkeypatch):
    f = tmp_path / "telegram_owner.txt"
    monkeypatch.setattr(tb, "_owner_file", lambda: f)
    tb._save_owner(999888777)  # owner claims first
    tb._save_owner(111)        # owner later /allows a smaller ID
    lines = f.read_text().splitlines()
    assert lines[0] == "999888777"
    assert "111" in lines


def test_save_owner_no_duplicates(tmp_path, monkeypatch):
    f = tmp_path / "telegram_owner.txt"
    monkeypatch.setattr(tb, "_owner_file", lambda: f)
    tb._save_owner(42)
    tb._save_owner(42)
    assert f.read_text().splitlines() == ["42"]
