"""
illip repair — standalone recovery when ILLIP is stuck or won't start.

Deliberately imports NOTHING from the app (if app code is broken, this must
still run) and uses only the stdlib. Deterministic steps, no AI guesswork:

  1. Kill a stuck server on port 8000
  2. Make sure Ollama is up (start it if not)
  3. Smoke-test the code (import app.main in a subprocess)
  4. If broken: offer git rollback — local changes first, then origin/main
     (origin/main is CI-tested on every push, so it is a known-good state)
  5. Reinstall dependencies if imports are missing
  6. Restart the server and wait for /api/health

Run via:  illip repair
"""

import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Windows terminals default to cp1252 — emoji/box chars crash print() without this
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
PORT = 8000
OLLAMA = "http://localhost:11434"
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

fixed: list[str] = []


def say(msg: str) -> None:
    print(f"  {msg}")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def http_ok(url: str, timeout: float = 3) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def step_kill_stuck_server() -> None:
    print("\n[1/6] Stuck server check")
    out = run(["netstat", "-ano"]).stdout
    pids = set()
    for line in out.splitlines():
        if f":{PORT} " in line and "LISTENING" in line:
            m = re.search(r"(\d+)\s*$", line)
            if m:
                pids.add(m.group(1))
    if not pids:
        say("no server on port 8000")
        return
    for pid in pids:
        run(["taskkill", "/PID", pid, "/F"])
        say(f"killed stuck process {pid}")
        fixed.append(f"killed stuck server (pid {pid})")


def step_ollama() -> None:
    print("\n[2/6] Ollama")
    if http_ok(f"{OLLAMA}/api/version"):
        say("running")
        return
    say("not running — starting…")
    try:
        subprocess.Popen(["ollama", "serve"], creationflags=DETACHED,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        say("!! ollama not installed — get it from https://ollama.com")
        return
    for _ in range(15):
        time.sleep(1)
        if http_ok(f"{OLLAMA}/api/version"):
            say("Ollama started")
            fixed.append("restarted Ollama")
            return
    say("!! Ollama did not come up — try rebooting, or reinstall from ollama.com")


def smoke_test() -> str:
    """Empty string = code imports fine, else the error text."""
    r = run([sys.executable, "-c", "import app.main"], timeout=120)
    return "" if r.returncode == 0 else (r.stderr.strip()[-800:] or "unknown import error")


def ask(question: str) -> bool:
    try:
        return input(f"  {question} [y/N] ").strip().lower() == "y"
    except EOFError:
        return False


def step_code() -> bool:
    print("\n[3/6] Code smoke test")
    err = smoke_test()
    if not err:
        say("code imports cleanly")
        return True
    say("code is BROKEN:")
    print("  ┌" + "─" * 60)
    for line in err.splitlines()[-6:]:
        print(f"  │ {line}")
    print("  └" + "─" * 60)

    # Missing dependency? Reinstall is safe, try before touching git.
    if "ModuleNotFoundError" in err:
        say("missing dependency — reinstalling requirements…")
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], timeout=900)
        fixed.append("reinstalled dependencies")
        err = smoke_test()
        if not err:
            say("fixed by dependency reinstall")
            return True

    # Local uncommitted changes broke it?
    dirty = run(["git", "status", "--porcelain"]).stdout.strip()
    if dirty:
        say("you have uncommitted local changes — they may be the cause:")
        for line in dirty.splitlines()[:8]:
            say(f"   {line}")
        if ask("Discard these local changes (reset to last commit)?"):
            run(["git", "checkout", "--", "."])
            fixed.append("discarded broken local changes")
            if not smoke_test():
                say("fixed by discarding local changes")
                return True

    # A bad commit? origin/main is CI-tested green on every push.
    if ask("Reset code to origin/main (last CI-tested version)? Local commits are kept in git reflog."):
        run(["git", "fetch", "origin"], timeout=120)
        run(["git", "reset", "--hard", "origin/main"])
        fixed.append("reset code to origin/main")
        if not smoke_test():
            say("fixed by resetting to origin/main")
            return True

    say("!! still broken — send the error above to your assistant")
    return False


def step_frontend() -> None:
    print("\n[4/6] Frontend")
    if (ROOT / "frontend" / "dist" / "index.html").exists():
        say("dist present")
    else:
        say("!! frontend/dist missing — run: cd frontend && npm run build (or git reset restored it)")


def step_models() -> None:
    print("\n[5/6] Models")
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
            models = json.load(r).get("models", [])
        if models:
            say(f"{len(models)} model(s) installed")
        else:
            say("!! no models — open ILLIP and use the Get Models panel, or: ollama pull llama3.2:3b")
    except Exception:
        say("could not list models (Ollama not up)")


def step_restart() -> None:
    print("\n[6/6] Restarting ILLIP")
    # Same launch style as illip.bat: own minimized window, fully independent
    # of this script's terminal (a plain detached Popen dies with some shells).
    subprocess.Popen(
        f'start "ILLIP" /min "{sys.executable}" -m uvicorn app.main:app --port {PORT}',
        cwd=ROOT, shell=True,
    )
    for i in range(60):
        time.sleep(1)
        if http_ok(f"http://localhost:{PORT}/api/health", timeout=3):
            say(f"ILLIP is UP → http://localhost:{PORT}")
            fixed.append("restarted the server")
            return
        if i == 20:
            say("still starting (model warmup)…")
    say("!! server did not come up in 60s — check the ILLIP window for errors")


def main() -> None:
    print("🔧 ILLIP repair — deterministic recovery, no AI guesswork\n" + "═" * 50)
    step_kill_stuck_server()
    step_ollama()
    code_ok = step_code()
    step_frontend()
    step_models()
    if code_ok:
        step_restart()
    else:
        say("skipping restart — code still broken")
    print("\n" + "═" * 50)
    if fixed:
        print("Repaired: " + "; ".join(fixed))
    else:
        print("Nothing needed fixing — if it still feels stuck, run /doctor in the chat.")


if __name__ == "__main__":
    main()
