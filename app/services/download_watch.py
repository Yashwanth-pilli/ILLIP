"""
Downloads auto-watch — background loop that runs the Guardian's heuristic
scan on newly-finished downloads and queues an alert when something looks
malicious, so the user is warned without having to remember to /scan.

Design notes:
  * Heuristics only in the loop (collect_findings) — fast, no LLM, no Defender
    subprocess. The user can still run the full `/scan` for the deep check.
  * Skips partial downloads (.crdownload/.part/.tmp) and anything modified in
    the last 3s, so we scan the finished file, not one mid-write.
  * State is in-memory: a set of already-seen paths + a queue of alerts the
    frontend drains via GET /api/guardian/alerts. No disk writes.
  * Off by default? No — it's read-only and cheap, but it only alerts on
    danger/warn findings, never on clean files (no notification spam).
"""

import asyncio
import time
from pathlib import Path

from app.services.file_guardian import collect_findings
from app.utils import logger

_POLL_INTERVAL = 20          # seconds between Downloads sweeps
_SETTLE_SECONDS = 3          # ignore files still being written
_PARTIAL_EXTS = {".crdownload", ".part", ".tmp", ".partial", ".download"}

_seen: set[str] = set()      # paths already scanned this session
_alerts: list[dict] = []     # pending alerts for the frontend to drain
_watch_task: asyncio.Task | None = None
_primed = False              # first pass just records existing files, no alerts


def _downloads_dir() -> Path:
    return Path.home() / "Downloads"


def drain_alerts() -> list[dict]:
    """Return pending alerts and clear the queue (frontend polls this)."""
    global _alerts
    out, _alerts = _alerts, []
    return out


def _scan_new_files() -> None:
    """One sweep: scan finished files we haven't seen, queue danger/warn alerts."""
    global _primed
    d = _downloads_dir()
    if not d.exists():
        return
    now = time.time()
    for p in d.iterdir():
        try:
            if not p.is_file():
                continue
            key = str(p.resolve()).lower()
            if key in _seen:
                continue
            if p.suffix.lower() in _PARTIAL_EXTS:
                continue  # still downloading — check again next sweep
            age = now - p.stat().st_mtime
            if 0 <= age < _SETTLE_SECONDS:
                continue  # just touched, let it settle
            _seen.add(key)
            if not _primed:
                continue  # first run only records the backlog, never alerts on it
            findings, _ = collect_findings(p)
            dangers = [f for f in findings if f["level"] == "danger"]
            warns = [f for f in findings if f["level"] == "warn"]
            if dangers or warns:
                level = "danger" if dangers else "warn"
                top = (dangers or warns)[0]["message"]
                _alerts.append({
                    "level": level,
                    "file": p.name,
                    "path": str(p),
                    "message": top,
                })
                logger.info(f"download_watch: {level} on {p.name}")
        except (OSError, PermissionError) as e:
            logger.debug(f"download_watch skip {p}: {e}")


async def _loop() -> None:
    global _primed
    await asyncio.sleep(10)
    _scan_new_files()   # prime: record existing downloads without alerting
    _primed = True
    while True:
        try:
            _scan_new_files()
        except Exception as e:
            logger.debug(f"download_watch loop error (non-fatal): {e}")
        await asyncio.sleep(_POLL_INTERVAL)


def start_download_watch() -> None:
    """Start the background Downloads watcher. Safe to call once at startup."""
    global _watch_task
    import os
    if "PYTEST_CURRENT_TEST" in os.environ:
        return  # never run the real-Downloads loop during tests
    if _watch_task is not None and not _watch_task.done():
        return
    try:
        _watch_task = asyncio.get_event_loop().create_task(_loop())
        logger.info("DownloadWatch: started (scans new downloads every 20s)")
    except RuntimeError:
        logger.debug("DownloadWatch: no event loop yet")
