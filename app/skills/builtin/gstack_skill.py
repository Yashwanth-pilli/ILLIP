"""
gstack skill — lets the agent crew inspect a git repo (branch, status,
staged changes, recent commits, a suggested commit message) during a task.

READ-ONLY: it never commits, pushes, or mutates the repo — same guarantee as
the /gstack chat command it wraps.
"""

from app.skills.base_skill import BaseSKill


class GstackSkill(BaseSKill):
    name = "git_status"
    description = (
        "Inspect a git repository read-only: current branch, changed/staged "
        "files, recent commits, and a suggested conventional-commit message for "
        "staged changes. Never commits or pushes. Pass the repo path, or leave "
        "empty for ILLIP's own repo."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute path to the git repo (empty = ILLIP's own)."},
        },
        "required": [],
    }

    async def execute(self, path: str = "", **_) -> str:
        from app.api.routes.gstack import gstack_report
        return await gstack_report(path or "")
