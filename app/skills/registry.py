"""
SkillRegistry — central registry for all plugins/skills.
"""

from typing import Dict
from app.skills.base_skill import BaseSKill
from app.utils import logger


class SkillRegistry:
    def __init__(self):
        self._skills: Dict[str, BaseSKill] = {}

    def register(self, skill: BaseSKill) -> None:
        self._skills[skill.name] = skill
        logger.info(f"Skill registered: {skill.name}")

    def get(self, name: str) -> BaseSKill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]

    def to_tool_specs(self) -> list[dict]:
        return [s.to_tool_spec() for s in self._skills.values()]

    async def run(self, name: str, args: dict) -> str:
        skill = self._skills.get(name)
        if not skill:
            return f"Error: skill '{name}' not found. Available: {list(self._skills)}"
        try:
            result = await skill.execute(**args)
            logger.info(f"Skill '{name}' executed -> {str(result)[:80]}")
            return result
        except Exception as e:
            logger.error(f"Skill '{name}' failed: {e}")
            return f"Error running skill '{name}': {e}"


_registry = SkillRegistry()


def get_registry() -> SkillRegistry:
    return _registry
