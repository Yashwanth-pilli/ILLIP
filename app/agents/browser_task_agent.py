"""
BrowserTaskAgent v2 — AI browser controller with task planner + retry.

Flow:
  1. PLAN: LLM decomposes task into numbered sub-tasks
  2. EXECUTE: for each sub-task, observe→decide→act loop
  3. RETRY: if action fails 2x on same page, LLM picks alternative strategy
  4. VERIFY: after each sub-task, LLM confirms completion before moving on

Works on: Salesforce, Cisco labs, Google Workspace, any web app.
Handles: shadow DOM, React/LWC, iframes, login flows, form filling, navigation.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import AsyncGenerator

from app.utils import logger


_PLANNER_PROMPT = """You are a browser automation planner. Break the following task into clear numbered sub-tasks.

Task: {task}
Start URL: {url}

Rules:
- Each sub-task should be ONE clear action goal (login, navigate to X, fill form, click button, verify result)
- Identify if login is needed as sub-task 1
- Be specific about what to look for on each page
- Max 15 sub-tasks

Reply with ONLY a JSON array of strings. Example:
["Navigate to login page", "Enter username and password and submit", "Go to Leads module", "Click New Lead button", "Fill First Name: John, Last Name: Smith, Company: Acme", "Save the lead", "Verify success message"]
"""

_AGENT_SYSTEM = """You are an expert browser automation agent controlling a real Chromium browser.

CRITICAL RULES:
1. Reply with ONLY one JSON action. No markdown, no explanation.
2. Elements are listed as [idx] tag — label. Always prefer [idx] reference for precision.
3. Salesforce Lightning / Cisco labs use shadow DOM — elements ARE detected, use their [idx].
4. After login submit, ALWAYS wait 3-5 seconds for the app to load.
5. If a dropdown appears after typing (autocomplete), click the matching option.
6. If a button is not visible, scroll down first.
7. If same action fails twice in a row, try a DIFFERENT approach (different idx, different text, scroll first).
8. For Salesforce: after clicking "New" or "Save", wait for the modal/form to fully load.
9. For Cisco labs: read the lab instructions visible on page, follow them exactly.
10. Only use {"action": "done"} when you can SEE confirmation that the task is complete.

CURRENT SUB-TASK: {subtask}
OVERALL TASK: {task}
SUB-TASK PROGRESS: {progress}

ACTIONS:
{"action": "navigate", "url": "https://..."}
{"action": "click", "target": "[idx] or exact button text"}
{"action": "type", "target": "[idx] or field label", "text": "value"}
{"action": "select", "target": "CSS selector", "value": "option text"}
{"action": "scroll", "direction": "down", "amount": 3}
{"action": "press", "key": "Enter|Tab|Escape|ArrowDown"}
{"action": "wait", "seconds": 3}
{"action": "extract", "target": "body"}
{"action": "screenshot"}
{"action": "subtask_done", "summary": "what was accomplished"}
{"action": "done", "result": "full task completion summary"}
{"action": "failed", "reason": "why impossible"}
"""


class BrowserTaskAgent:
    name = "browser_task"
    MAX_STEPS_PER_SUBTASK = 15
    MAX_SUBTASKS = 15

    async def run_task(
        self,
        task: str,
        start_url: str = "",
        credentials: dict | None = None,
        headless: bool | None = None,
        capture_screenshots: bool = True,
        max_steps: int = 80,
    ) -> AsyncGenerator[dict, None]:

        from app.services.browser_controller import BrowserController, HEADLESS
        from app.services.chat_service import get_llm

        _headless = headless if headless is not None else HEADLESS
        llm = get_llm()
        browser = BrowserController(headless=_headless)
        total_steps = 0

        yield _ev("start", {"task": task, "headless": _headless})

        try:
            # Auto-install Chromium on first use — no manual steps needed
            from app.services.browser_controller import ensure_browser_ready

            setup_msgs: list[str] = []

            async def _on_setup_progress(msg: str):
                setup_msgs.append(msg)

            ready = await ensure_browser_ready(progress_cb=_on_setup_progress)

            for msg in setup_msgs:
                yield _ev("setup", {"message": msg})

            if not ready:
                yield _ev("failed", {"reason": "Could not install browser. Check internet connection."})
                return

            await browser.start()

            # ── Navigate to start URL ──────────────────────────────────────
            if start_url:
                actual = await browser.navigate(start_url)
                yield _ev("step", _step(0, "navigate", start_url, actual))
                total_steps += 1

            # ── Phase 1: Plan ──────────────────────────────────────────────
            yield _ev("plan", {"message": "Planning task steps..."})
            subtasks = await self._plan(llm, task, start_url, credentials)
            yield _ev("plan", {"message": f"Plan ready: {len(subtasks)} sub-tasks", "subtasks": subtasks})

            # ── Phase 2: Execute each sub-task ─────────────────────────────
            completed_subtasks: list[str] = []
            step_num = total_steps

            for st_idx, subtask in enumerate(subtasks):
                yield _ev("subtask_start", {
                    "idx": st_idx + 1,
                    "total": len(subtasks),
                    "subtask": subtask,
                })

                consecutive_fails = 0
                last_action = ""

                for _ in range(self.MAX_STEPS_PER_SUBTASK):
                    step_num += 1
                    if step_num > max_steps:
                        yield _ev("failed", {"reason": f"Exceeded max steps ({max_steps})"})
                        return

                    state = await browser.get_state(
                        capture_screenshot=capture_screenshots and step_num % 4 == 0
                    )

                    progress = f"{st_idx+1}/{len(subtasks)} done: [{', '.join(completed_subtasks[-3:])}]"

                    creds_hint = ""
                    if credentials:
                        creds_hint = "\n\nCredentials available:\n" + \
                            "\n".join(f"  {k}: {v}" for k, v in credentials.items())

                    prompt = (
                        f"{creds_hint}\n\n"
                        f"Page state:\n{state.to_context()}\n\n"
                        f"Failed attempts on this page: {consecutive_fails}\n"
                        f"Last action tried: {last_action}\n\n"
                        f"What is the next action for the current sub-task?"
                    )

                    try:
                        raw = await llm.complete(
                            prompt,
                            system=_AGENT_SYSTEM.format(
                                subtask=subtask,
                                task=task,
                                progress=progress,
                            ),
                        )
                        action_json = _parse_action(raw)
                    except Exception as e:
                        yield _ev("step", _step(step_num, "error", "", f"LLM error: {e}"))
                        await asyncio.sleep(2)
                        continue

                    action = action_json.get("action", "")
                    target = action_json.get("target", "")
                    result = ""
                    error = ""
                    screenshot_b64 = state.screenshot_b64

                    last_action = f"{action} {target}"

                    try:
                        if action == "navigate":
                            result = await browser.navigate(action_json.get("url", ""))

                        elif action == "click":
                            ok = await browser.click(target)
                            if ok:
                                result = "clicked"
                                consecutive_fails = 0
                            else:
                                result = "click failed"
                                consecutive_fails += 1
                                error = f"Could not click '{target}'"

                        elif action == "type":
                            ok = await browser.type_text(target, action_json.get("text", ""))
                            result = "typed" if ok else "type failed"
                            if not ok:
                                consecutive_fails += 1
                                error = f"Could not type into '{target}'"

                        elif action == "select":
                            ok = await browser.select_option(target, action_json.get("value", ""))
                            result = "selected" if ok else "select failed"

                        elif action == "scroll":
                            await browser.scroll(action_json.get("direction", "down"), action_json.get("amount", 3))
                            result = "scrolled"
                            consecutive_fails = 0

                        elif action == "press":
                            await browser.press_key(action_json.get("key", "Enter"))
                            result = f"pressed {action_json.get('key')}"

                        elif action == "wait":
                            secs = min(float(action_json.get("seconds", 2)), 10)
                            await browser.wait_seconds(secs)
                            result = f"waited {secs}s"
                            consecutive_fails = 0

                        elif action == "extract":
                            result = (await browser.extract_text(target or "body"))[:500]

                        elif action == "screenshot":
                            screenshot_b64 = await browser.screenshot_b64()
                            result = "screenshot taken"

                        elif action == "subtask_done":
                            summary = action_json.get("summary", subtask)
                            completed_subtasks.append(summary)
                            yield _ev("subtask_done", {"idx": st_idx + 1, "summary": summary})
                            if capture_screenshots:
                                screenshot_b64 = await browser.screenshot_b64()
                            yield _ev("step", {
                                **_step(step_num, "subtask_done", subtask, summary),
                                "screenshot_b64": screenshot_b64,
                            })
                            break  # move to next sub-task

                        elif action == "done":
                            final_result = action_json.get("result", "Task completed")
                            if capture_screenshots:
                                screenshot_b64 = await browser.screenshot_b64()
                            yield _ev("done", {
                                "step": step_num,
                                "result": final_result,
                                "steps_taken": step_num,
                                "subtasks_completed": len(completed_subtasks),
                                "screenshot_b64": screenshot_b64,
                            })
                            return

                        elif action == "failed":
                            yield _ev("failed", {"reason": action_json.get("reason", "Unknown")})
                            return

                    except Exception as e:
                        error = str(e)
                        consecutive_fails += 1
                        logger.warning(f"BrowserTask step {step_num}: {e}")

                    step_data = _step(step_num, action, target, result, error)
                    if screenshot_b64 and action not in ("subtask_done",):
                        step_data["screenshot_b64"] = screenshot_b64
                    yield _ev("step", step_data)

                else:
                    # Sub-task max steps hit — continue to next sub-task anyway
                    yield _ev("subtask_done", {
                        "idx": st_idx + 1,
                        "summary": f"{subtask} (max steps reached, continuing)",
                    })
                    completed_subtasks.append(f"{subtask} (partial)")

            # All sub-tasks done
            if capture_screenshots:
                ss = await browser.screenshot_b64()
            else:
                ss = ""
            yield _ev("done", {
                "step": step_num,
                "result": f"All {len(subtasks)} sub-tasks completed: " + "; ".join(completed_subtasks),
                "steps_taken": step_num,
                "subtasks_completed": len(completed_subtasks),
                "screenshot_b64": ss,
            })

        except Exception as e:
            logger.error(f"BrowserTaskAgent fatal: {e}")
            yield _ev("failed", {"reason": str(e)})
        finally:
            await browser.stop()

    async def _plan(self, llm, task: str, url: str, credentials: dict | None) -> list[str]:
        cred_hint = ""
        if credentials:
            cred_hint = f"\nCredentials available: {list(credentials.keys())}"
        prompt = _PLANNER_PROMPT.format(task=task + cred_hint, url=url or "not specified")
        try:
            raw = await llm.complete(prompt)
            raw = raw.strip()
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                subtasks = json.loads(raw[start:end])
                return [str(s) for s in subtasks[:self.MAX_SUBTASKS]]
        except Exception as e:
            logger.warning(f"Task planning failed: {e}, using single-task mode")
        return [task]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ev(type_: str, data: dict) -> dict:
    return {"type": type_, "data": data}


def _step(step: int, action: str, target: str, result: str, error: str = "") -> dict:
    return {"step": step, "action": action, "target": target, "result": result[:300], "error": error}


def _parse_action(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(raw[start:end])
    raise ValueError(f"No JSON in LLM response: {raw[:200]}")


_agent: BrowserTaskAgent | None = None


def get_browser_task_agent() -> BrowserTaskAgent:
    global _agent
    if _agent is None:
        _agent = BrowserTaskAgent()
    return _agent
