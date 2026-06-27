"""
Time utilities for ILLIP AI
"""

from datetime import datetime, timezone
from typing import Optional


def get_current_timestamp() -> datetime:
    """Get current timestamp in UTC"""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime object"""
    return dt.strftime(format_str)


def iso_timestamp(dt: Optional[datetime] = None) -> str:
    """Get ISO format timestamp"""
    if dt is None:
        dt = get_current_timestamp()
    return dt.isoformat()


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp"""
    return datetime.fromisoformat(timestamp_str)
