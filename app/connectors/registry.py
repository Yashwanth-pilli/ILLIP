"""
ConnectorRegistry — auto-discovers and manages all connectors.

Built-in connectors live in app/connectors/.
User-dropped connectors live in data/connectors/ (no code change needed).

To add a new integration:
  1. Subclass BaseConnector
  2. Drop the .py file in data/connectors/
  3. Restart ILLIP — it auto-loads and starts if env vars are set

HTTP-only integrations (Zapier, Make, any webhook) need zero code —
use the /webhooks endpoint to register inbound triggers.
"""

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Optional
from app.connectors.base_connector import BaseConnector
from app.utils import logger
from app.config import settings

# Built-in connector module paths: (module_path, class_attr)
_BUILTIN_CONNECTORS = [
    ("app.connectors.discord_bot",    "DiscordConnector"),
    ("app.connectors.slack_bot",      "SlackConnector"),
    ("app.connectors.email_connector","EmailConnector"),
    ("app.connectors.n8n_connector",  "N8nConnector"),
    ("app.connectors.whatsapp_connector", "WhatsAppConnector"),
]

_USER_CONNECTORS_DIR = settings.get_data_path() / "connectors"


class ConnectorRegistry:
    def __init__(self):
        self._connectors: dict[str, BaseConnector] = {}

    def _load_builtin(self):
        for mod_path, cls_name in _BUILTIN_CONNECTORS:
            try:
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name, None)
                if cls and issubclass(cls, BaseConnector):
                    instance = cls()
                    self._connectors[instance.name] = instance
            except Exception as e:
                logger.warning(f"Connector load failed [{mod_path}]: {e}")

    def _load_user_connectors(self):
        """Load .py files from data/connectors/ — user-defined integrations."""
        _USER_CONNECTORS_DIR.mkdir(parents=True, exist_ok=True)
        for py_file in _USER_CONNECTORS_DIR.glob("*.py"):
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[py_file.stem] = mod
                spec.loader.exec_module(mod)
                for _, cls in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(cls, BaseConnector) and cls is not BaseConnector:
                        instance = cls()
                        self._connectors[instance.name] = instance
                        logger.info(f"Loaded user connector: {instance.name}")
            except Exception as e:
                logger.warning(f"User connector load failed [{py_file.name}]: {e}")

    async def start_all(self):
        self._load_builtin()
        self._load_user_connectors()
        for name, connector in self._connectors.items():
            if connector.is_configured():
                try:
                    ok = await connector.start()
                    logger.info(f"Connector '{name}': {'started' if ok else 'start failed'}")
                except Exception as e:
                    logger.warning(f"Connector '{name}' start error: {e}")
            else:
                missing = connector.missing_vars()
                logger.debug(f"Connector '{name}' skipped — missing: {missing}")

    async def stop_all(self):
        for name, connector in self._connectors.items():
            if connector.is_active():
                try:
                    await connector.stop()
                except Exception as e:
                    logger.warning(f"Connector '{name}' stop error: {e}")

    async def start_one(self, name: str) -> dict:
        connector = self._connectors.get(name)
        if not connector:
            return {"error": f"Connector '{name}' not found"}
        if not connector.is_configured():
            return {"error": "Not configured", "missing": connector.missing_vars()}
        ok = await connector.start()
        return {"started": ok, "active": connector.is_active()}

    async def stop_one(self, name: str) -> dict:
        connector = self._connectors.get(name)
        if not connector:
            return {"error": f"Connector '{name}' not found"}
        await connector.stop()
        return {"stopped": True}

    def get(self, name: str) -> Optional[BaseConnector]:
        return self._connectors.get(name)

    def all_status(self) -> list[dict]:
        return [c.to_status() for c in self._connectors.values()]

    def reload_user_connectors(self):
        """Hot-reload user connectors from data/connectors/ without restart."""
        self._load_user_connectors()
        return list(self._connectors.keys())


_registry: Optional[ConnectorRegistry] = None


def get_connector_registry() -> ConnectorRegistry:
    global _registry
    if _registry is None:
        _registry = ConnectorRegistry()
    return _registry
