"""
Package installer skill — safe pip install with human approval gate.
ILLIP never auto-installs without user confirmation.
"""

import asyncio
import sys
import re
from app.skills.base_skill import BaseSKill
from app.utils import logger

# Blocked packages — security risk
_BLOCKED = {
    "setuptools-git", "colourama", "python3-dateutil",  # known typosquats
    "urllib", "os", "sys",  # stdlib names used as malicious packages
}

# Safe known packages ILLIP may need
_KNOWN_SAFE = {
    "pdfplumber", "pypdf", "pypdf2", "pillow", "numpy", "pandas",
    "matplotlib", "seaborn", "scikit-learn", "transformers", "torch",
    "sentence-transformers", "chromadb", "faiss-cpu", "tiktoken",
    "whisper", "openai-whisper", "faster-whisper",
    "piper-tts", "sounddevice", "pyaudio",
    "requests", "httpx", "aiohttp", "beautifulsoup4", "lxml",
    "python-docx", "openpyxl", "python-pptx",
    "gitpython", "pygments", "rich", "typer", "click",
}


def _validate_package_name(name: str) -> tuple[bool, str]:
    """Basic security check on package name."""
    name = name.strip().lower().split("==")[0].split(">=")[0].split("<=")[0]
    if not re.match(r'^[a-z0-9][a-z0-9\-_.]*$', name):
        return False, f"Invalid package name: '{name}'"
    if name in _BLOCKED:
        return False, f"Package '{name}' is blocked for security reasons."
    return True, name


class PackageInstallerSkill(BaseSKill):
    name = "install_package"
    description = (
        "Install a Python package via pip. Requires explicit user approval before installing. "
        "Use when a skill or feature needs a missing library."
    )
    parameters = {
        "type": "object",
        "properties": {
            "package": {
                "type": "string",
                "description": "Package name to install (e.g. 'pdfplumber', 'numpy==1.26.0')",
            },
            "confirmed": {
                "type": "boolean",
                "description": "Set true only after user explicitly confirmed installation.",
            },
        },
        "required": ["package"],
    }

    async def execute(self, package: str, confirmed: bool = False, **_) -> str:
        valid, result = _validate_package_name(package)
        if not valid:
            return result

        clean_name = result

        # Safety gate — never install without explicit confirmation
        if not confirmed:
            known = clean_name in _KNOWN_SAFE
            safety_note = "(known safe package)" if known else "(unknown package — verify before confirming)"
            return (
                f"Ready to install: {package} {safety_note}\n"
                f"To confirm, run this skill again with confirmed=true.\n"
                f"Or in terminal: pip install {package}"
            )

        logger.info(f"Installing package: {package}")
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                # Find "Successfully installed" line
                for line in out.splitlines():
                    if "Successfully installed" in line:
                        return f"Installed: {line.replace('Successfully installed', '').strip()}"
                return f"Installed {package} successfully."
            else:
                return f"Install failed:\n{err.strip()[:500]}"
        except asyncio.TimeoutError:
            return f"Install timed out for '{package}'. Try manually: pip install {package}"
        except Exception as e:
            return f"Install error: {e}"
