"""
Read file skill — read files from the workspace directory only (sandboxed).
"""

from pathlib import Path
from app.skills.base_skill import BaseSKill
from app.config import settings


class ReadFileSkill(BaseSKill):
    name = "read_file"
    description = (
        "Read a file from the user's workspace. Only files inside the workspace "
        "directory are accessible. Use to inspect uploaded documents or code files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path relative to the workspace directory.",
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum lines to return (default 100).",
            },
        },
        "required": ["path"],
    }

    async def execute(self, path: str, max_lines: int = 100, **_) -> str:
        workspace = settings.get_workspaces_path().resolve()
        target = (workspace / path).resolve()

        # Sandbox: must stay inside workspace
        if not str(target).startswith(str(workspace)):
            return "Error: Access denied — path is outside the workspace directory."
        if not target.exists():
            return f"Error: File not found: {path}"
        if not target.is_file():
            return f"Error: '{path}' is not a file."

        try:
            text = target.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()[: int(max_lines)]
            truncated = len(text.splitlines()) > int(max_lines)
            result = "\n".join(lines)
            if truncated:
                result += f"\n\n[... truncated at {max_lines} lines]"
            return result or "(empty file)"
        except Exception as e:
            return f"Error reading file: {e}"
