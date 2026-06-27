"""
Plugin API — create / list / delete user-defined connectors.

POST   /api/plugins/          — create or update plugin from JSON spec
GET    /api/plugins/          — list all plugins
GET    /api/plugins/{name}    — get one plugin spec
DELETE /api/plugins/{name}    — delete plugin
GET    /api/plugins/templates — example specs for common connector types
"""

from fastapi import APIRouter, HTTPException
from app.plugins.registry import save_plugin, delete_plugin, list_plugins, _plugins_dir
import json

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("/templates")
async def get_templates():
    """Example plugin specs the user can copy and fill in."""
    return {
        "templates": [
            {
                "name": "my_weather",
                "display_name": "Weather (wttr.in)",
                "description": "Get current weather for any city — free, no key needed",
                "plugin_type": "http",
                "config": {
                    "url": "https://wttr.in/{city}?format=3",
                    "method": "GET",
                    "headers": {},
                    "body_template": "",
                },
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name, e.g. London"}
                    },
                    "required": ["city"],
                },
            },
            {
                "name": "my_notion",
                "display_name": "Notion Search",
                "description": "Search your Notion workspace",
                "plugin_type": "http",
                "config": {
                    "url": "https://api.notion.com/v1/search",
                    "method": "POST",
                    "headers": {
                        "Authorization": "Bearer YOUR_NOTION_TOKEN",
                        "Notion-Version": "2022-06-28",
                        "Content-Type": "application/json",
                    },
                    "body_template": '{"query": "{query}"}',
                },
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What to search for in Notion"}
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "my_webhook",
                "display_name": "Custom Webhook",
                "description": "POST data to any webhook URL (n8n, Zapier, etc.)",
                "plugin_type": "http",
                "config": {
                    "url": "https://your-webhook-url.com/hook",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body_template": '{"message": "{message}", "source": "illip"}',
                },
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to send to webhook"}
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "my_github_status",
                "display_name": "GitHub Repo Status",
                "description": "Get info about any GitHub repo",
                "plugin_type": "http",
                "config": {
                    "url": "https://api.github.com/repos/{owner}/{repo}",
                    "method": "GET",
                    "headers": {"Accept": "application/vnd.github+json"},
                    "body_template": "",
                },
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "GitHub username or org"},
                        "repo":  {"type": "string", "description": "Repository name"},
                    },
                    "required": ["owner", "repo"],
                },
            },
        ]
    }


@router.get("/")
async def list_all_plugins():
    return {"plugins": list_plugins(), "count": len(list_plugins())}


@router.get("/{name}")
async def get_plugin(name: str):
    path = _plugins_dir() / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/")
async def create_or_update_plugin(spec: dict):
    """
    Create or update a plugin. Spec must have: name, plugin_type, config, parameters.
    Immediately usable — no restart needed.
    """
    if not spec.get("name"):
        raise HTTPException(status_code=400, detail="spec.name required")
    if not spec.get("plugin_type"):
        spec["plugin_type"] = "http"
    path = save_plugin(spec)
    return {"status": "registered", "name": spec["name"], "path": str(path)}


@router.delete("/{name}")
async def remove_plugin(name: str):
    ok = delete_plugin(name)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
    return {"status": "deleted", "name": name}
