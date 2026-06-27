"""Planner agent — breaks goals into actionable tasks using LLM."""

from typing import Optional, Dict, Any
from app.agents.base_agent import BaseAgent
from app.utils import logger


class PlannerAgent(BaseAgent):

    def __init__(self):
        super().__init__("planner", "Planner Agent", prompt_file="planner_prompt.md")

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"PlannerAgent: {task_input[:80]}")
        return await self._call_llm(task_input, context)
