"""
Skill + Connector installer — install from any URL, zero disk waste.

Supported URL types:
  - Raw Python file URL  → fetched into memory, exec'd, registered. No disk write.
  - GitHub repo URL      → cloned to temp dir, registered, then offers cleanup.
  - PyPI package name    → pip install, then import and register.

Flow:
  install_from_url(url) → InstallResult
    .installed     bool
    .names         list of skill/connector names registered
    .cleanup_needed  bool — True if temp dir was created
    .temp_path     str | None — path to delete if cleanup_needed
    .prompt        str — message to show user ("Keep folder or delete?")
"""

import asyncio
import importlib
import inspect
import os
import shutil
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.utils import logger


@dataclass
class InstallResult:
    installed: bool
    names: list[str] = field(default_factory=list)
    cleanup_needed: bool = False
    temp_path: str | None = None
    prompt: str = ""
    error: str = ""
    validation: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "installed": self.installed,
            "names": self.names,
            "cleanup_needed": self.cleanup_needed,
            "temp_path": self.temp_path,
            "prompt": self.prompt,
            "error": self.error,
            "validation": self.validation,
        }


def _find_and_register_classes(mod: types.ModuleType) -> list[str]:
    """Scan module for BaseSKill / BaseConnector subclasses and register them."""
    from app.skills.base_skill import BaseSKill
    from app.skills.registry import get_registry
    from app.connectors.base_connector import BaseConnector
    from app.connectors.registry import get_connector_registry

    registered = []

    for _, cls in inspect.getmembers(mod, inspect.isclass):
        if cls.__module__ != mod.__name__ and cls.__module__ != "__exec__":
            continue  # skip imported base classes

        # Skill
        if issubclass(cls, BaseSKill) and cls is not BaseSKill:
            try:
                instance = cls()
                get_registry().register(instance)
                registered.append(f"skill:{instance.name}")
                logger.info(f"URL-installed skill: {instance.name}")
            except Exception as e:
                logger.warning(f"Skill class {cls.__name__} failed to instantiate: {e}")

        # Connector
        if issubclass(cls, BaseConnector) and cls is not BaseConnector:
            try:
                instance = cls()
                get_connector_registry()._connectors[instance.name] = instance
                registered.append(f"connector:{instance.name}")
                logger.info(f"URL-installed connector: {instance.name}")
            except Exception as e:
                logger.warning(f"Connector class {cls.__name__} failed to instantiate: {e}")

    return registered


async def _install_raw_file(url: str) -> InstallResult:
    """Fetch a single .py file, validate, exec in memory, register. Zero disk write."""
    from app.skills.validator import validate_code

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            code = r.text
    except Exception as e:
        return InstallResult(installed=False, error=f"Fetch failed: {e}")

    mod_name = Path(url.split("?")[0]).stem

    # Safety gate — block dangerous code before exec
    vr = await validate_code(code, source_name=mod_name)
    if vr.blocked:
        return InstallResult(
            installed=False,
            error=f"Safety blocked: {vr.blocked_reason}",
            validation=vr.to_dict(),
        )

    mod = types.ModuleType(mod_name)
    mod.__name__ = "__exec__"
    try:
        exec(compile(code, url, "exec"), mod.__dict__)  # noqa: S102
    except Exception as e:
        return InstallResult(installed=False, error=f"Exec failed: {e}", validation=vr.to_dict())

    sys.modules[mod_name] = mod
    names = _find_and_register_classes(mod)

    if not names:
        return InstallResult(
            installed=False,
            error="No BaseSKill or BaseConnector subclass found in file.",
            validation=vr.to_dict(),
        )

    return InstallResult(
        installed=True,
        names=names,
        cleanup_needed=False,
        prompt=f"Skill/connector '{', '.join(names)}' integrated from URL. No files saved to disk.",
        validation=vr.to_dict(),
    )


def _parse_github_url(url: str) -> tuple[str, str, str]:
    """
    Parse GitHub URL into (owner, repo, branch).
    Handles:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/main
      https://github.com/owner/repo.git
    """
    url = url.rstrip("/").removesuffix(".git")
    parts = url.replace("https://github.com/", "").split("/")
    owner = parts[0] if len(parts) > 0 else ""
    repo  = parts[1] if len(parts) > 1 else ""
    branch = parts[3] if len(parts) > 3 and parts[2] == "tree" else "main"
    return owner, repo, branch


async def _fetch_github_file_list(owner: str, repo: str, branch: str, token: str = "") -> list[dict]:
    """Use GitHub contents API to list .py files. No git, no disk."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Fetch repo tree (recursive) — one API call gets all paths
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    async with httpx.AsyncClient(timeout=20, headers=headers) as c:
        r = await c.get(url)
        if r.status_code == 404:
            # Try 'master' branch if 'main' not found
            url2 = url.replace(f"/{branch}?", "/master?")
            r = await c.get(url2)
        r.raise_for_status()
        tree = r.json().get("tree", [])

    # Only .py files not in __pycache__, tests, or hidden dirs
    py_files = [
        item for item in tree
        if item["type"] == "blob"
        and item["path"].endswith(".py")
        and not any(p.startswith((".", "_", "test", "setup", "conf"))
                    for p in item["path"].split("/"))
    ]
    return py_files


async def _install_github_repo(repo_url: str) -> InstallResult:
    """
    Install from GitHub repo URL — fully in memory, zero disk write.

    Uses GitHub Contents API to list .py files, fetches each via raw URL,
    exec's in memory. No git clone. No temp dir. No disk usage.
    """
    import os

    # Convert github.com URL → raw content base
    owner, repo, branch = _parse_github_url(repo_url)
    if not owner or not repo:
        return InstallResult(installed=False, error=f"Cannot parse GitHub URL: {repo_url}")

    gh_token = os.getenv("GITHUB_TOKEN", "")  # optional — avoids rate limits

    # Step 1: list all .py files in repo via API
    try:
        py_files = await _fetch_github_file_list(owner, repo, branch, gh_token)
    except Exception as e:
        return InstallResult(installed=False, error=f"GitHub API error: {e}. Set GITHUB_TOKEN env var to avoid rate limits.")

    if not py_files:
        return InstallResult(installed=False, error="No .py files found in repo.")

    # Step 2: check for requirements.txt — install deps first
    headers = {"Accept": "application/vnd.github+json"}
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"

    req_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/requirements.txt"
    try:
        async with httpx.AsyncClient(timeout=10, headers=headers) as c:
            r = await c.get(req_url)
        if r.status_code == 200:
            reqs = [
                line.strip() for line in r.text.splitlines()
                if line.strip() and not line.startswith("#")
            ]
            if reqs:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pip", "install", *reqs, "-q",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.communicate()
                logger.info(f"GitHub repo deps installed: {reqs}")
    except Exception:
        pass  # requirements.txt optional

    # Step 3: fetch + validate + exec each .py file in memory
    from app.skills.validator import validate_code

    registered: list[str] = []
    errors: list[str] = []
    all_warnings: list[str] = []
    blocked_files: list[str] = []

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        for item in py_files:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{item['path']}"
            try:
                r = await c.get(raw_url)
                r.raise_for_status()
                code = r.text
            except Exception as e:
                errors.append(f"{item['path']}: fetch failed ({e})")
                continue

            mod_name = Path(item["path"]).stem

            # Safety gate per file — skip dangerous files, don't abort whole repo
            vr = await validate_code(code, source_name=mod_name)
            if vr.blocked:
                blocked_files.append(f"{item['path']}: {vr.blocked_reason}")
                logger.warning(f"Blocked file in {owner}/{repo}: {item['path']} — {vr.blocked_reason}")
                continue
            all_warnings.extend(vr.warnings)

            mod = types.ModuleType(mod_name)
            mod.__name__ = "__exec__"
            try:
                exec(compile(code, raw_url, "exec"), mod.__dict__)  # noqa: S102
                sys.modules[mod_name] = mod
                found = _find_and_register_classes(mod)
                registered.extend(found)
            except Exception as e:
                errors.append(f"{item['path']}: exec failed ({e})")

    # If ALL files were blocked, hard fail
    if not registered and blocked_files:
        return InstallResult(
            installed=False,
            error=f"All files blocked by safety scan: {'; '.join(blocked_files[:3])}",
            validation={"blocked_files": blocked_files, "warnings": all_warnings},
        )

    if not registered:
        err_detail = "; ".join(errors[:3]) if errors else "no BaseSKill/BaseConnector subclass found"
        return InstallResult(installed=False, error=f"Nothing registered. {err_detail}")

    warn_summary = f" {len(all_warnings)} warning(s)." if all_warnings else ""
    blocked_summary = f" {len(blocked_files)} file(s) blocked by safety scan." if blocked_files else ""

    return InstallResult(
        installed=True,
        names=registered,
        cleanup_needed=False,
        prompt=(
            f"'{', '.join(registered)}' integrated from {owner}/{repo} — "
            f"fully in memory, zero disk used.{warn_summary}{blocked_summary} "
            f"Add persist=true to save to data/connectors/ for auto-load on restart."
        ),
        validation={
            "warnings": all_warnings,
            "blocked_files": blocked_files,
            "files_scanned": len(py_files),
            "files_registered": len(registered),
        },
    )


async def _install_pypi(package: str) -> InstallResult:
    """pip install a package, then auto-discover skill/connector classes."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "pip", "install", package, "-q",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        return InstallResult(installed=False, error=f"pip install failed: {stderr.decode()[:300]}")

    # Try to import the package and scan for classes
    pkg_name = package.split(">=")[0].split("==")[0].split("[")[0].replace("-", "_")
    try:
        mod = importlib.import_module(pkg_name)
        registered = _find_and_register_classes(mod)
    except ImportError:
        registered = []

    return InstallResult(
        installed=True,
        names=registered or [f"package:{pkg_name}"],
        cleanup_needed=False,
        prompt=f"Package '{package}' installed. {'Classes registered: ' + str(registered) if registered else 'No auto-registered classes found — import manually.'}",
    )


async def install_from_url(url: str) -> InstallResult:
    """
    Main entry point. Auto-detects URL type and installs.

    Supports:
      https://raw.githubusercontent.com/.../*.py  → memory exec, no disk
      https://github.com/user/repo                → git clone, cleanup prompt
      pypi:some-package                           → pip install
    """
    url = url.strip()

    if url.startswith("pypi:"):
        return await _install_pypi(url[5:].strip())

    if url.endswith(".py") or "raw.githubusercontent.com" in url or "/raw/" in url:
        return await _install_raw_file(url)

    if "github.com" in url or url.endswith(".git"):
        return await _install_github_repo(url)

    # Try as raw file first, fall back to GitHub repo
    if url.startswith("http"):
        result = await _install_raw_file(url)
        if result.installed:
            return result
        return await _install_github_repo(url)

    return InstallResult(installed=False, error=f"Cannot determine install type for: {url}")


async def cleanup_temp(temp_path: str) -> bool:
    """Delete downloaded temp folder after user confirms."""
    try:
        shutil.rmtree(temp_path, ignore_errors=False)
        logger.info(f"Cleaned up temp dir: {temp_path}")
        return True
    except Exception as e:
        logger.error(f"Cleanup failed for {temp_path}: {e}")
        return False


def save_to_user_connectors(url: str, code: str) -> str:
    """
    Optionally persist a URL-fetched skill to data/connectors/ so it
    survives restarts. Returns the saved path.
    """
    from app.config import settings
    dest_dir = settings.get_data_path() / "connectors"
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = Path(url.split("?")[0]).stem
    dest = dest_dir / f"{name}.py"
    dest.write_text(code)
    return str(dest)
