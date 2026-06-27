"""
Datetime skill — returns current date/time.
"""

from datetime import datetime
from app.skills.base_skill import BaseSKill


class DatetimeSkill(BaseSKill):
    name = "get_datetime"
    description = (
        "Get the current date and time. Use when asked about today's date, "
        "current time, day of the week, or what year/month it is."
    )
    parameters = {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "description": (
                    "Optional strftime format string. "
                    "Default returns human-readable full datetime."
                ),
            }
        },
        "required": [],
    }

    async def execute(self, format: str = None, **_) -> str:
        now = datetime.now()
        if format:
            try:
                return now.strftime(format)
            except Exception:
                pass
        return now.strftime("%A, %B %d, %Y at %I:%M %p")
