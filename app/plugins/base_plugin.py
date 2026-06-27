"""
BasePlugin — extends BaseSKill with connection config.

A plugin = a skill that needs user config (API key, URL, etc.).
Users define plugins as JSON files in data/plugins/.
The system auto-registers each as a usable skill.
"""

from app.skills.base_skill import BaseSKill


class BasePlugin(BaseSKill):
    """
    Plugin base. Subclass this for custom connector types.
    Set `config_schema` to describe what the user must configure.
    """
    config_schema: dict = {}   # JSON Schema for required config fields
    plugin_type: str = "generic"

    def __init__(self, config: dict):
        self.config = config   # filled from data/plugins/<name>.json

    def to_plugin_spec(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "plugin_type": self.plugin_type,
            "parameters": self.parameters,
            "config_schema": self.config_schema,
            "configured": bool(self.config),
        }
