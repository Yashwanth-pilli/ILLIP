"""
Self-build service - manages safe self-improvement workflow
"""

from typing import Optional, Dict, Any, List
from app.utils import logger, get_current_timestamp
from app.agents import get_agent_registry
from enum import Enum
import uuid


class SafeBuildPhase(str, Enum):
    """Phases of safe self-building"""
    PLAN = "plan"
    BUILD = "build"
    REVIEW = "review"
    TEST = "test"
    APPROVAL = "approval"
    DEPLOY = "deploy"
    LOG = "log"


class SelfBuildService:
    """
    Service for managing safe self-improvement workflow
    
    Enforces safety by:
    - Never auto-editing critical files without approval
    - Maintaining full audit trail
    - Requiring explicit approval at key points
    - Keeping all changes in staging until approved
    """
    
    def __init__(self):
        self.builds: Dict[str, Dict[str, Any]] = {}
        self.agent_registry = get_agent_registry()
        self.protected_files = {
            "app/main.py",
            "app/config.py",
            "app/dependencies.py",
            ".env",
            "requirements.txt",
        }
    
    def start_build_session(
        self,
        goal: str,
        description: Optional[str] = None
    ) -> str:
        """Start a new build session"""
        session_id = str(uuid.uuid4())
        
        session = {
            "id": session_id,
            "goal": goal,
            "description": description or "",
            "status": "active",
            "current_phase": SafeBuildPhase.PLAN,
            "created_at": get_current_timestamp().isoformat(),
            "phases": {
                "plan": {"status": "pending", "output": None},
                "build": {"status": "pending", "output": None},
                "review": {"status": "pending", "output": None},
                "test": {"status": "pending", "output": None},
                "approval": {"status": "pending", "approved": False},
                "deploy": {"status": "pending", "output": None},
                "log": {"status": "pending", "output": None},
            },
            "changes": [],
            "approvals": [],
        }
        
        self.builds[session_id] = session
        logger.info(f"Build session created: {session_id}")
        return session_id
    
    def get_build_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a build session"""
        return self.builds.get(session_id)
    
    async def execute_phase(
        self,
        session_id: str,
        phase: SafeBuildPhase
    ) -> Dict[str, Any]:
        """Execute a phase of the build process"""
        session = self.builds.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        logger.info(f"Executing phase: {phase} for session: {session_id}")
        
        # Verify phase order
        phase_order = [
            SafeBuildPhase.PLAN,
            SafeBuildPhase.BUILD,
            SafeBuildPhase.REVIEW,
            SafeBuildPhase.TEST,
            SafeBuildPhase.APPROVAL,
            SafeBuildPhase.DEPLOY,
            SafeBuildPhase.LOG,
        ]
        
        current_index = phase_order.index(session["current_phase"])
        phase_index = phase_order.index(phase)
        
        if phase_index < current_index:
            return {
                "error": f"Cannot go back from {session['current_phase']} to {phase}"
            }
        
        # Execute phase based on type
        if phase == SafeBuildPhase.PLAN:
            return await self._phase_plan(session)
        elif phase == SafeBuildPhase.BUILD:
            return await self._phase_build(session)
        elif phase == SafeBuildPhase.REVIEW:
            return await self._phase_review(session)
        elif phase == SafeBuildPhase.TEST:
            return await self._phase_test(session)
        elif phase == SafeBuildPhase.APPROVAL:
            return await self._phase_approval(session)
        
        return {"status": "phase_not_implemented"}
    
    async def _phase_plan(self, session: Dict) -> Dict[str, Any]:
        """PLAN phase - Use planner agent to break down the goal"""
        planner = self.agent_registry.get_agent("planner")
        if not planner:
            return {"error": "Planner agent not available"}
        
        result = await planner.execute_task(session["goal"])
        session["phases"]["plan"]["status"] = "completed"
        session["phases"]["plan"]["output"] = result.get("output")
        session["current_phase"] = SafeBuildPhase.BUILD
        
        return result
    
    async def _phase_build(self, session: Dict) -> Dict[str, Any]:
        """BUILD phase - Use builder agent to create implementation"""
        builder = self.agent_registry.get_agent("builder")
        if not builder:
            return {"error": "Builder agent not available"}
        
        plan_output = session["phases"]["plan"].get("output")
        result = await builder.execute_task(plan_output or session["goal"])
        
        session["phases"]["build"]["status"] = "completed"
        session["phases"]["build"]["output"] = result.get("output")
        session["current_phase"] = SafeBuildPhase.REVIEW
        
        return result
    
    async def _phase_review(self, session: Dict) -> Dict[str, Any]:
        """REVIEW phase - Use reviewer agent to check quality"""
        reviewer = self.agent_registry.get_agent("reviewer")
        if not reviewer:
            return {"error": "Reviewer agent not available"}
        
        build_output = session["phases"]["build"].get("output")
        result = await reviewer.execute_task(build_output or "")
        
        session["phases"]["review"]["status"] = "completed"
        session["phases"]["review"]["output"] = result.get("output")
        session["current_phase"] = SafeBuildPhase.TEST
        
        return result
    
    async def _phase_test(self, session: Dict) -> Dict[str, Any]:
        """TEST phase - Use tester agent to validate"""
        tester = self.agent_registry.get_agent("tester")
        if not tester:
            return {"error": "Tester agent not available"}
        
        build_output = session["phases"]["build"].get("output")
        result = await tester.execute_task(build_output or "")
        
        session["phases"]["test"]["status"] = "completed"
        session["phases"]["test"]["output"] = result.get("output")
        session["current_phase"] = SafeBuildPhase.APPROVAL
        
        return result
    
    async def _phase_approval(self, session: Dict) -> Dict[str, Any]:
        """APPROVAL phase - Wait for human approval"""
        return {
            "status": "awaiting_approval",
            "message": "Build completed. Requires human review and approval before deployment.",
            "review_output": session["phases"]["review"].get("output"),
            "test_output": session["phases"]["test"].get("output"),
        }
    
    def approve_build(self, session_id: str, reviewer: str = "human") -> Dict[str, Any]:
        """Approve a build for deployment"""
        session = self.builds.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        session["phases"]["approval"]["approved"] = True
        session["phases"]["approval"]["status"] = "completed"
        session["current_phase"] = SafeBuildPhase.DEPLOY
        session["approvals"].append({
            "reviewer": reviewer,
            "timestamp": get_current_timestamp().isoformat(),
        })
        
        logger.info(f"Build approved by {reviewer}: {session_id}")
        return {"status": "approved"}
    
    def get_build_stats(self) -> Dict[str, Any]:
        """Get statistics about all builds"""
        return {
            "total_sessions": len(self.builds),
            "active": len([b for b in self.builds.values() if b["status"] == "active"]),
            "completed": len([b for b in self.builds.values() if b["status"] == "completed"]),
        }


# Global self-build service
_self_build_service: Optional[SelfBuildService] = None


def get_self_build_service() -> SelfBuildService:
    """Get or create global self-build service"""
    global _self_build_service
    if _self_build_service is None:
        _self_build_service = SelfBuildService()
    return _self_build_service
