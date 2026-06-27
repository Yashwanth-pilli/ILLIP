"""Tester agent — designs and validates tests using LLM."""

from typing import Optional, Dict, Any
from app.agents.base_agent import BaseAgent
from app.utils import logger


class TesterAgent(BaseAgent):

    def __init__(self):
        super().__init__("tester", "Tester Agent", prompt_file="tester_prompt.md")

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"TesterAgent: {task_input[:80]}")
        return await self._call_llm(task_input, context)
