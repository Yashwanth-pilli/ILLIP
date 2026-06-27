"""
Workspace service - manages workspaces and environments
"""

from typing import Optional, Dict, Any
from app.utils import logger, get_current_timestamp, get_workspaces_path
from pathlib import Path
import uuid


class WorkspaceService:
    """Service for managing workspaces"""
    
    def __init__(self):
        self.workspaces: Dict[str, Dict[str, Any]] = {}
        self.data_dir = get_workspaces_path()
        self.current_workspace: Optional[str] = None
    
    def create_workspace(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new workspace"""
        workspace_id = str(uuid.uuid4())
        
        workspace = {
            "id": workspace_id,
            "name": name,
            "description": description or "",
            "created_at": get_current_timestamp().isoformat(),
            "updated_at": get_current_timestamp().isoformat(),
            "status": "active",
            "file_count": 0,
        }
        
        self.workspaces[workspace_id] = workspace
        logger.info(f"Workspace created: {workspace_id}")
        
        # Set as current if first workspace
        if not self.current_workspace:
            self.current_workspace = workspace_id
        
        return workspace
    
    def get_current_workspace(self) -> Optional[Dict[str, Any]]:
        """Get current workspace"""
        if not self.current_workspace:
            return None
        return self.workspaces.get(self.current_workspace)
    
    def set_current_workspace(self, workspace_id: str) -> bool:
        """Set current workspace"""
        if workspace_id in self.workspaces:
            self.current_workspace = workspace_id
            logger.info(f"Current workspace set to: {workspace_id}")
            return True
        return False
    
    def list_workspaces(self) -> Dict[str, Any]:
        """List all workspaces"""
        return {
            "workspaces": list(self.workspaces.values()),
            "current": self.current_workspace,
            "total": len(self.workspaces),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workspace statistics"""
        return {
            "total_workspaces": len(self.workspaces),
            "current_workspace": self.current_workspace,
        }


# Global workspace service
_workspace_service: Optional[WorkspaceService] = None


def get_workspace_service() -> WorkspaceService:
    """Get or create global workspace service"""
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service
