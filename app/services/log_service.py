"""
Log service - handles application logging
"""

from typing import Optional, List, Dict, Any
from app.utils import logger, get_current_timestamp, get_logs_path
import uuid


class LogService:
    """Service for managing application logs"""
    
    def __init__(self):
        self.logs: Dict[str, Dict[str, Any]] = {}
        self.max_logs = 1000  # Keep last 1000 logs in memory
    
    def log(
        self,
        level: str,
        message: str,
        source: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Log a message"""
        log_id = str(uuid.uuid4())
        log_entry = {
            "id": log_id,
            "level": level,
            "message": message,
            "source": source,
            "timestamp": get_current_timestamp().isoformat(),
            "metadata": metadata or {},
        }
        
        self.logs[log_id] = log_entry
        
        # Trim logs if too many
        if len(self.logs) > self.max_logs:
            # Remove oldest entries
            oldest_ids = sorted(
                self.logs.keys(),
                key=lambda k: self.logs[k]["timestamp"]
            )[:len(self.logs) - self.max_logs]
            for log_id_to_remove in oldest_ids:
                del self.logs[log_id_to_remove]
        
        return log_id
    
    def info(self, message: str, source: Optional[str] = None):
        """Log info message"""
        return self.log("INFO", message, source)
    
    def warning(self, message: str, source: Optional[str] = None):
        """Log warning message"""
        return self.log("WARNING", message, source)
    
    def error(self, message: str, source: Optional[str] = None):
        """Log error message"""
        return self.log("ERROR", message, source)
    
    def debug(self, message: str, source: Optional[str] = None):
        """Log debug message"""
        return self.log("DEBUG", message, source)
    
    def get_logs(
        self,
        level: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get logs with optional filtering"""
        logs = list(self.logs.values())
        
        if level:
            logs = [l for l in logs if l["level"] == level]
        
        # Sort by timestamp descending (newest first)
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return logs[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get log statistics"""
        levels = {}
        for log in self.logs.values():
            level = log.get("level", "UNKNOWN")
            levels[level] = levels.get(level, 0) + 1
        
        return {
            "total_logs": len(self.logs),
            "by_level": levels,
        }


# Global log service
_log_service: Optional[LogService] = None


def get_log_service() -> LogService:
    """Get or create global log service"""
    global _log_service
    if _log_service is None:
        _log_service = LogService()
    return _log_service
