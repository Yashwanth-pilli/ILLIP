"""
Model/Agent service - manages LLM providers and agents
"""

from typing import Optional, List, Dict, Any
from app.providers import get_provider, ProviderFactory
from app.agents import get_agent_registry
from app.utils import logger


class ModelService:
    """Service for managing LLM model providers"""
    
    async def get_provider_status(self) -> Dict[str, Any]:
        """Get current provider status"""
        provider = await get_provider()
        return {
            "name": provider.name,
            "is_available": provider.is_available,
            "last_error": provider.last_error,
        }
    
    def list_available_providers(self) -> List[str]:
        """List available providers"""
        return ProviderFactory.list_providers()


class AgentService:
    """Service for managing agents"""
    
    def __init__(self):
        self.registry = get_agent_registry()
    
    def list_agents(self) -> Dict[str, Any]:
        """List all agents and their status"""
        return {
            "agents": self.registry.get_all_agents_status(),
            "available_count": len(self.registry.get_available_agents()),
            "total_count": len(self.registry.agents),
        }
    
    def get_agent_status(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get status of specific agent"""
        return self.registry.get_agent_status(agent_type)
    
    async def execute_agent_task(
        self,
        agent_type: str,
        task_input: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a task using an agent"""
        agent = self.registry.get_agent(agent_type)
        if not agent:
            return {
                "status": "error",
                "error": f"Agent {agent_type} not found",
            }
        
        if not agent.is_available:
            return {
                "status": "error",
                "error": f"Agent {agent_type} is not available",
            }
        
        logger.info(f"Executing task with {agent_type} agent")
        return await agent.execute_task(task_input, context)


# Global services
_model_service: Optional[ModelService] = None
_agent_service: Optional[AgentService] = None


def get_model_service() -> ModelService:
    """Get or create global model service"""
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
    return _model_service


def get_agent_service() -> AgentService:
    """Get or create global agent service"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
