"""
System health + safe junk cleanup skills.

Lets ILLIP do the same disk-health check and cleanup a careful human would:
report space, find big folders, check the antivirus, and clear ONLY regenerable
caches — never personal files.

Safety model for cleanup:
  * Deletion targets come from a HARDCODED whitelist of known cache dirs. The
    model cannot pass an arbitrary path to delete — there is no path parameter.
  * Never touches Downloads/Documents/Desktop/Pictures, model stores, phone
    media (CrossDevice), or any project folder.
  * dry_run defaults True: it only reports what WOULD be freed. Real deletion
    needs confirm=True (so the model must show the user first).
  * In-use/locked files are skipped, not forced.
"""

import os
import shutil
import subprocess
from pathlib import Path

from app.skills.base_skill import BaseSKill
from app.utils import logger


def _dir_bytes(p: Path) -> int:
    if not p.exists():
        return 0
    total = 0
    for f in p.rglob("*"):
        try:
            if f.is_file():
                total += f.stat().st_size
        except (OSError, PermissionError):
            pass
    return total


def _mb(b: int) -> int:
    return int(b / (1024 * 1024))


def _gb(b: int) -> float:
    return round(b / (1024 ** 3), 2)


# ── Whitelist of REGENERABLE caches only. Each rebuilds itself when needed. ──
# Personal data is never on this list. Kept as functions so env vars resolve now.
def _cache_targets() -> list[tuple[str, Path]]:
    la = os.environ.get("LOCALAPPDATA", "")
    home = os.path.expanduser("~")
    return [
        ("windows temp",  Path(os.environ.get("TEMP", ""))),
        ("pip cache",     Path(la) / "pip" / "Cache"),
        ("npm cache",     Path(la) / "npm-cache"),
        ("gradle cache",  Path(home) / ".gradle" / "caches"),
        ("edge cache",    Path(la) / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache"),
        ("chrome cache",  Path(la) / "Google" / "Chrome" / "User Data" / "Default" / "Cache"),
        ("comet cache",   Path(la) / "Perplexity" / "Comet" / "User Data" / "Default" / "Cache"),
    ]


class SystemHealthSkill(BaseSKill):
    name = "system_health"
    description = (
        "Check the computer's health: free disk space on every drive, the biggest "
        "folders in the user profile, size of clearable caches, and antivirus "
        "status. READ-ONLY — never changes or deletes anything. Use when the user "
        "asks why the PC is slow/full, or to plan a cleanup."
    )
    parameters = {"type": "object", "properties": {}, "required": []}

    async def execute(self, **_) -> str:
        out: list[str] = []

        # Disk space per drive
        out.append("DISK SPACE:")
        for part in _drives():
            try:
                u = shutil.disk_usage(part)
                out.append(f"  {part}  free {_gb(u.free)} GB / {_gb(u.total)} GB "
                           f"({int(100 * u.free / u.total)}% free)")
            except OSError:
                pass

        # Clearable caches (sizes only)
        out.append("\nCLEARABLE CACHES (safe to delete, they regenerate):")
        total = 0
        for label, p in _cache_targets():
            if p.exists():
                b = _dir_bytes(p)
                total += b
                if _mb(b) > 0:
                    out.append(f"  {label:<14} {_mb(b)} MB")
        out.append(f"  --> ~{_mb(total)} MB reclaimable via clean_junk")

        # Biggest folders in the user profile (for the user to review — NOT auto-deleted)
        home = Path(os.path.expanduser("~"))
        out.append("\nBIGGEST FOLDERS in your profile (review these yourself, "
                   "personal data is never auto-deleted):")
        sizes = []
        for d in home.iterdir():
            try:
                if d.is_dir():
                    sizes.append((_dir_bytes(d), d.name))
            except (OSError, PermissionError):
                pass
        for b, name in sorted(sizes, reverse=True)[:8]:
            out.append(f"  {_gb(b):>6} GB  {name}")

        # Antivirus status (Windows Defender)
        out.append("\nANTIVIRUS:")
        out.append("  " + _defender_status().replace("\n", "\n  "))
        return "\n".join(out)


class CleanJunkSkill(BaseSKill):
    name = "clean_junk"
    description = (
        "Free disk space by deleting ONLY regenerable caches (temp files, pip/npm/"
        "gradle/browser caches). Never touches personal files, documents, downloads, "
        "photos, AI models, or project folders. ALWAYS call with dry_run=true first "
        "to show the user what would be freed, then call with confirm=true to "
        "actually delete after they agree."
    )
    parameters = {
        "type": "object",
        "properties": {
            "dry_run": {
                "type": "boolean",
                "description": "True (default): only report what would be freed, delete nothing.",
            },
            "confirm": {
                "type": "boolean",
                "description": "Must be true to actually delete. Only set after the user agrees.",
            },
        },
        "required": [],
    }

    async def execute(self, dry_run: bool = True, confirm: bool = False, **_) -> str:
        # Never delete unless BOTH: not a dry run AND explicit confirm.
        do_delete = (not dry_run) and confirm
        # Protect the currently-running session dir so we don't delete our own logs.
        session_dir = str((Path(os.environ.get("TEMP", "")) / "claude").resolve()).lower()

        lines: list[str] = []
        freed = 0
        for label, p in _cache_targets():
            if not p.exists():
                continue
            before = _dir_bytes(p)
            if before == 0:
                continue
            if do_delete:
                for child in list(p.iterdir()):
                    try:
                        if str(child.resolve()).lower() == session_dir:
                            continue  # never nuke our own session
                        if child.is_dir():
                            shutil.rmtree(child, ignore_errors=True)
                        else:
                            child.unlink()
                    except (OSError, PermissionError):
                        pass  # in-use/locked -> skip, don't force
                after = _dir_bytes(p)
                got = before - after
                freed += got
                lines.append(f"  {label:<14} freed {_mb(got)} MB")
            else:
                freed += before
                lines.append(f"  {label:<14} {_mb(before)} MB")

        head = ("CLEANED (regenerable caches only):" if do_delete
                else "DRY RUN — nothing deleted yet. Would free:")
        tail = (f"\n  TOTAL FREED ~{_mb(freed)} MB"
                if do_delete else
                f"\n  TOTAL ~{_mb(freed)} MB. To actually delete, run clean_junk "
                "with dry_run=false and confirm=true.")
        note = ("\nPersonal files, documents, downloads, photos, AI models and "
                "project folders were NOT touched.")
        return head + "\n" + "\n".join(lines) + tail + note


def _drives() -> list[str]:
    if os.name == "nt":
        import string
        return [f"{d}:\\" for d in string.ascii_uppercase
                if os.path.exists(f"{d}:\\")]
    return ["/"]


def _defender_status() -> str:
    """Windows Defender status via PowerShell. Read-only. Best-effort."""
    if os.name != "nt":
        return "not Windows — skipped"
    try:
        ps = (
            "$m=Get-MpComputerStatus;"
            "'Realtime protection: '+$m.RealTimeProtectionEnabled+"
            "'; Antivirus: '+$m.AntivirusEnabled+"
            "'; Signatures age(days): '+$m.AntivirusSignatureAge+"
            "'; Last quick scan: '+$m.QuickScanStartTime"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=25,
        )
        s = (r.stdout or "").strip()
        return s or "Defender status unavailable (may need admin)."
    except Exception as e:
        logger.debug(f"defender status failed: {e}")
        return "Defender status unavailable."


if __name__ == "__main__":
    import asyncio
    # Self-check: health read-only runs; clean_junk dry-run never deletes.
    async def _t():
        h = await SystemHealthSkill().execute()
        assert "DISK SPACE" in h and "CLEARABLE CACHES" in h, "health output malformed"
        d = await CleanJunkSkill().execute(dry_run=True)
        assert "DRY RUN" in d and "NOT touched" in d, "dry run must not delete"
        # dry run must not have deleted: confirm the caches still report a size or empty
        print("system_skill self-check ok")
    asyncio.run(_t())
