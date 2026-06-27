"""
Plugin registry — loads user-defined plugins from data/plugins/*.json
and registers each as a skill so agents + chat tool-call loop can use them.

Lifecycle:
  1. On startup: scan data/plugins/*.json, build HTTPPlugin/etc, register in SkillRegistry
  2. On POST /api/plugins/ (create): write JSON, hot-register without restart
  3. On DELETE /api/plugins/{name}: unregister from SkillRegistry, delete file
"""

import json
from pathlib import Path
from app.config import settings
from app.utils import logger


def _plugins_dir() -> Path:
    p = settings.get_data_path() / "plugins"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _build_plugin(spec: dict):
    ptype = spec.get("plugin_type", "http")
    if ptype == "http":
        from app.plugins.http_plugin import HTTPPlugin
        return HTTPPlugin(spec)
    # Future: "webhook", "python", "grpc", etc.
    return None


def load_all_plugins() -> list:
    """Load all plugin JSON files and return plugin instances."""
    plugins = []
    for f in sorted(_plugins_dir().glob("*.json")):
        try:
            spec = json.loads(f.read_text(encoding="utf-8"))
            plugin = _build_plugin(spec)
            if plugin:
                plugins.append(plugin)
                logger.info(f"Plugin loaded: {plugin.name} ({spec.get('plugin_type','http')})")
        except Exception as e:
            logger.warning(f"Plugin load failed {f.name}: {e}")
    return plugins


def register_all_plugins() -> int:
    """Load all plugins and register them in the skill registry. Returns count."""
    from app.skills.registry import get_registry
    reg = get_registry()
    plugins = load_all_plugins()
    for p in plugins:
        reg.register(p)
    return len(plugins)


def save_plugin(spec: dict) -> Path:
    """Persist a plugin spec to disk and hot-register it."""
    name = spec["name"]
    path = _plugins_dir() / f"{name}.json"
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    # Hot-register
    plugin = _build_plugin(spec)
    if plugin:
        from app.skills.registry import get_registry
        get_registry().register(plugin)
        logger.info(f"Plugin hot-registered: {name}")
    return path


def delete_plugin(name: str) -> bool:
    """Remove plugin from disk and unregister from skill registry."""
    path = _plugins_dir() / f"{name}.json"
    if not path.exists():
        return False
    path.unlink()
    from app.skills.registry import get_registry
    reg = get_registry()
    if name in reg._skills:
        del reg._skills[name]
        logger.info(f"Plugin unregistered: {name}")
    return True


def list_plugins() -> list[dict]:
    """Return all plugin specs from disk."""
    result = []
    for f in sorted(_plugins_dir().glob("*.json")):
        try:
            result.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return result
