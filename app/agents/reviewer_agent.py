"""Reviewer agent — reviews code and output using LLM."""

from typing import Optional, Dict, Any
from app.agents.base_agent import BaseAgent
from app.utils import logger


class ReviewerAgent(BaseAgent):

    def __init__(self):
        super().__init__("reviewer", "Reviewer Agent", prompt_file="reviewer_prompt.md")

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"ReviewerAgent: {task_input[:80]}")
        return await self._call_llm(task_input, context)
