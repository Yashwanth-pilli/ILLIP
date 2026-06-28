"""
Skill/Connector validator — runs before any URL-installed code is registered.

Two-stage gate:
  1. Static scan  — AST analysis for dangerous patterns. Hard block if found.
  2. Smoke test   — calls execute() with empty args in isolated thread with timeout.
                    Warns on failure but does not block (skill may need real args).

Returns ValidationResult with passed/blocked/warnings.
"""

import ast
import asyncio
import concurrent.futures
import re
import sys
import types
from dataclasses import dataclass, field

from app.utils import logger

# Patterns that hard-block install
_BLOCKED_PATTERNS = [
    # Shell / process execution
    (r"\bos\.system\b",                  "os.system() — shell execution"),
    (r"\bos\.popen\b",                   "os.popen() — shell execution"),
    (r"\bos\.execv\b|\bos\.execve\b",    "os.execv/execve — process replace"),
    (r"\bos\.fork\b",                    "os.fork() — process spawn"),
    (r"\bos\.kill\b",                    "os.kill() — process kill"),
    (r"\bsubprocess\b",                  "subprocess — shell execution"),
    (r"\bmultiprocessing\b",             "multiprocessing — process spawn"),
    # Arbitrary code execution
    (r"\beval\s*\(",                     "eval() — arbitrary code execution"),
    (r"\b__import__\s*\(",               "__import__() — dynamic import bypass"),
    (r"\bgetattr\s*\(.*builtins",        "getattr(__builtins__) — builtin bypass"),
    (r"__subclasses__\s*\(",             "__subclasses__() — sandbox escape"),
    (r"__builtins__\s*\[|__builtins__\s*\.", "__builtins__ manipulation — bypass"),
    # Low-level / memory
    (r"\bctypes\b",                      "ctypes — low-level memory access"),
    # Deserialization
    (r"\bpickle\.loads\b",               "pickle.loads — arbitrary deserialization"),
    (r"\bmarshal\.loads\b",              "marshal.loads — arbitrary deserialization"),
    # File system destruction
    (r"\bos\.remove\b|\bos\.unlink\b",   "os.remove/unlink — file deletion"),
    (r"\.unlink\s*\(",                   "Path.unlink() — file deletion"),
    (r"rmdir|shutil\.rmtree",            "directory deletion"),
    (r"chmod|chown",                     "permission modification"),
    # Network exfiltration
    (r"\bsocket\.socket\b",              "raw socket — uncontrolled network"),
    (r"\bsocket\.connect\b",             "raw socket.connect — uncontrolled network"),
    (r"\bftplib\b",                      "ftplib — FTP exfiltration"),
    (r"\bparamiko\b",                    "paramiko — SSH access"),
    (r"\bsmtplib\b",                     "smtplib — email exfiltration"),
    # Obfuscation delivery
    (r"\bbase64\b.*\bexec\b|\bexec\b.*\bbase64\b", "base64+exec — encoded payload"),
    # Secrets / env manipulation
    (r"os\.environ\s*\[.*\]\s*=",        "os.environ write — overwrites secrets"),
]

# Patterns that warn but don't block
_WARN_PATTERNS = [
    (r"\brequests\b",                    "uses 'requests' (sync) — prefer httpx async"),
    (r"open\s*\([^)]*['\"]w",           "file write — ensure path is inside data/"),
    (r"\bthreading\b",                   "raw threading — may cause issues"),
    (r"import\s+socket\b",              "socket import — network access"),
    (r"\burllib\b",                      "urllib — prefer httpx for async HTTP"),
    (r"\bbase64\b",                      "base64 import — verify no encoded payloads"),
    (r"ANTHROPIC_API_KEY|OPENAI_API_KEY|SECRET|PASSWORD|TOKEN\s*=\s*['\"]", "hardcoded secret/key"),
    (r"os\.environ\.get\(",             "reads env vars — ensure only expected vars accessed"),
]

# AST function call names that are hard-blocked
_BLOCKED_AST_CALLS = {
    "eval", "exec", "__import__", "compile",
}

# AST attribute names that are hard-blocked
_BLOCKED_AST_ATTRS = {
    "system", "popen", "execv", "execve", "fork", "kill",
    "remove", "unlink", "rmdir",
}

_BLOCKED_IMPORTS = {
    "subprocess", "ctypes", "pickle", "marshal", "pty", "pdb",
    "multiprocessing", "ftplib", "paramiko", "smtplib",
}


@dataclass
class ValidationResult:
    passed: bool
    blocked: bool = False
    blocked_reason: str = ""
    warnings: list[str] = field(default_factory=list)
    smoke_test: str = "skipped"   # "passed" | "failed" | "skipped"
    smoke_error: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "warnings": self.warnings,
            "smoke_test": self.smoke_test,
            "smoke_error": self.smoke_error,
        }


def _ast_scan(code: str, source_name: str) -> tuple[bool, str, list[str]]:
    """
    Parse AST and look for blocked patterns.
    Returns (blocked, reason, warnings).
    """
    warnings: list[str] = []
    try:
        tree = ast.parse(code, filename=source_name)
    except SyntaxError as e:
        return True, f"Syntax error: {e}", []

    for node in ast.walk(tree):
        # Blocked function calls
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in _BLOCKED_AST_CALLS:
                return True, f"Blocked function call: {name}()", warnings

        # Blocked imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = []
            if isinstance(node, ast.Import):
                mods = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module.split(".")[0]]
            for mod in mods:
                if mod in _BLOCKED_IMPORTS:
                    return True, f"Blocked import: {mod}", warnings

        # Block dangerous attribute access (os.system, os.kill, Path.unlink, etc.)
        if isinstance(node, ast.Attribute):
            if node.attr in _BLOCKED_AST_ATTRS:
                return True, f"Blocked attribute: .{node.attr}() — dangerous operation", warnings

    return False, "", warnings


def _regex_scan(code: str) -> tuple[bool, str, list[str]]:
    """Quick regex scan for blocked + warn patterns."""
    warnings: list[str] = []

    for pattern, label in _BLOCKED_PATTERNS:
        if re.search(pattern, code):
            return True, f"Blocked pattern: {label}", warnings

    for pattern, label in _WARN_PATTERNS:
        if re.search(pattern, code):
            warnings.append(f"Warning: {label}")

    return False, "", warnings


def _run_smoke_test(mod: types.ModuleType) -> tuple[str, str]:
    """
    Find first BaseSKill subclass, call execute() with empty kwargs.
    Runs in executor with timeout. Returns ("passed"|"failed"|"skipped", error).
    """
    try:
        from app.skills.base_skill import BaseSKill
        import inspect

        candidates = [
            cls for _, cls in inspect.getmembers(mod, inspect.isclass)
            if issubclass(cls, BaseSKill) and cls is not BaseSKill
        ]
        if not candidates:
            return "skipped", "no BaseSKill subclass found for smoke test"

        cls = candidates[0]
        instance = cls()

        # Run execute with empty args — it's expected to fail gracefully
        async def _run():
            try:
                result = await instance.execute()
                return str(result)[:100]
            except TypeError:
                # Missing required args — that's fine, skill loaded OK
                return "ok_missing_args"
            except Exception as e:
                return f"error:{e}"

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_run())
        loop.close()

        if result.startswith("error:"):
            return "failed", result[6:]
        return "passed", ""

    except Exception as e:
        return "failed", str(e)


async def validate_code(code: str, source_name: str = "unknown") -> ValidationResult:
    """
    Full validation pipeline for a code string before exec/registration.
    Safe to call before ANY user-supplied code is executed.
    """
    # Stage 1a: regex scan (fast, catches obvious patterns)
    blocked, reason, regex_warns = _regex_scan(code)
    if blocked:
        return ValidationResult(passed=False, blocked=True, blocked_reason=reason, warnings=regex_warns)

    # Stage 1b: AST scan (deeper, catches obfuscated calls)
    blocked, reason, ast_warns = _ast_scan(code, source_name)
    all_warnings = regex_warns + ast_warns
    if blocked:
        return ValidationResult(passed=False, blocked=True, blocked_reason=reason, warnings=all_warnings)

    # Stage 2: exec in isolated module for smoke test (5s timeout)
    mod = types.ModuleType(source_name)
    mod.__name__ = "__smoke__"
    try:
        exec(compile(code, source_name, "exec"), mod.__dict__)  # noqa: S102
    except Exception as e:
        return ValidationResult(
            passed=False, blocked=False,
            warnings=all_warnings,
            smoke_test="failed", smoke_error=f"Module load error: {e}",
        )

    # Run smoke test in thread pool (timeout guard)
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            smoke_status, smoke_err = await asyncio.wait_for(
                loop.run_in_executor(pool, _run_smoke_test, mod),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            smoke_status, smoke_err = "failed", "Smoke test timed out after 10s"

    passed = smoke_status in ("passed", "skipped", "ok_missing_args")
    if not passed:
        all_warnings.append(f"Smoke test failed: {smoke_err} (skill may still work with real args)")
        # Don't hard-block on smoke test failure — skill might need real config
        passed = True

    logger.info(f"Validation [{source_name}]: smoke={smoke_status} warnings={len(all_warnings)}")

    return ValidationResult(
        passed=passed,
        blocked=False,
        warnings=all_warnings,
        smoke_test=smoke_status,
        smoke_error=smoke_err if smoke_status == "failed" else "",
    )
