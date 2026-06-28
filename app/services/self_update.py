"""
Self-update system — checks GitHub for new commits, pulls, optionally restarts.

Usage (Telegram /update command):
  - check: compare local HEAD vs remote HEAD on main
  - pull:  git pull origin main
  - restart: restart uvicorn via os.execv (replaces process in-place)
"""

import asyncio
import os
import sys
from pathlib import Path
from app.utils import logger

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


async def get_local_hash() -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    return out.decode().strip()[:12]


async def get_remote_hash(branch: str = "main") -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", "-C", str(_REPO_ROOT), "ls-remote", "origin", f"refs/heads/{branch}",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    line = out.decode().strip()
    return line.split()[0][:12] if line else ""


async def check_update(branch: str = "main") -> dict:
    """Return update status dict."""
    local  = await get_local_hash()
    remote = await get_remote_hash(branch)
    up_to_date = (local == remote or not remote)
    return {
        "local": local,
        "remote": remote or "unknown",
        "up_to_date": up_to_date,
        "has_update": not up_to_date and bool(remote),
    }


async def pull_update(branch: str = "main") -> str:
    """git pull origin main. Returns stdout+stderr."""
    proc = await asyncio.create_subprocess_exec(
        "git", "-C", str(_REPO_ROOT), "pull", "origin", branch,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    output = out.decode().strip()
    logger.info(f"Self-update pull: {output[:200]}")
    return output


def restart_server():
    """Replace current process with a fresh uvicorn. No return."""
    logger.info("Self-update: restarting server...")
    os.execv(sys.executable, [sys.executable] + sys.argv)
