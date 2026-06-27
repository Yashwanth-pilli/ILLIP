"""Builder agent — generates code and implementations using LLM."""

from typing import Optional, Dict, Any
from app.agents.base_agent import BaseAgent
from app.utils import logger


class BuilderAgent(BaseAgent):

    def __init__(self):
        super().__init__("builder", "Builder Agent", prompt_file="builder_prompt.md")

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"BuilderAgent: {task_input[:80]}")
        return await self._call_llm(task_input, context)
