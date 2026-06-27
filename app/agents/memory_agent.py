"""Memory agent — stores, retrieves, and summarizes knowledge using LLM."""

from typing import Optional, Dict, Any
from app.agents.base_agent import BaseAgent
from app.utils import logger


class MemoryAgent(BaseAgent):

    def __init__(self):
        super().__init__("memory", "Memory Agent", prompt_file=None)
        self.memory_store: Dict[str, Any] = {}

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"MemoryAgent: {task_input[:80]}")

        if task_input.startswith("store:"):
            return await self._store_memory(task_input[6:].strip(), context)
        elif task_input.startswith("retrieve:"):
            return self._retrieve_memory(task_input[9:].strip())
        elif task_input.startswith("search:"):
            return self._search_memory(task_input[7:].strip())
        elif task_input.startswith("summarize:"):
            return await self._summarize(task_input[10:].strip(), context)
        else:
            # Free-form memory question — use LLM
            from app.core import Message
            from app.providers import get_provider
            from app.utils import get_current_timestamp

            store_summary = (
                f"Current memory store has {len(self.memory_store)} entries: "
                + ", ".join(list(self.memory_store.keys())[:10])
            ) if self.memory_store else "Memory store is empty."

            messages = [
                Message(
                    role="system",
                    content=(
                        "You are ILLIP's Memory Agent. Help the user store, find, and manage knowledge. "
                        + store_summary
                    ),
                    timestamp=get_current_timestamp(),
                ),
                Message(role="user", content=task_input, timestamp=get_current_timestamp()),
            ]
            provider = await get_provider()
            return await provider.safe_generate(messages=messages)

    async def _store_memory(self, data: str, context: Optional[Dict] = None) -> str:
        key = context.get("key", f"entry_{len(self.memory_store)}") if context else f"entry_{len(self.memory_store)}"
        self.memory_store[key] = data
        return f"Stored in memory with key: `{key}`"

    def _retrieve_memory(self, key: str) -> str:
        data = self.memory_store.get(key)
        return f"Memory[{key}]: {data}" if data else f"No memory found for key: `{key}`"

    def _search_memory(self, query: str) -> str:
        matches = {k: v for k, v in self.memory_store.items() if query.lower() in str(v).lower()}
        if matches:
            lines = [f"- **{k}**: {v}" for k, v in matches.items()]
            return f"Found {len(matches)} match(es):\n" + "\n".join(lines)
        return f"No memory matches for: `{query}`"

    async def _summarize(self, content: str, context: Optional[Dict] = None) -> str:
        prompt = f"Summarize the following for storage in memory:\n\n{content}"
        return await self._call_llm(prompt, context)

    def get_memory_stats(self) -> Dict[str, Any]:
        return {
            "total_entries": len(self.memory_store),
            "keys": list(self.memory_store.keys()),
        }
