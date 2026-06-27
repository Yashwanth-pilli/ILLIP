"""
HTTP Connector Plugin — call any REST API as a skill.

User defines in data/plugins/my_api.json:
{
  "name": "weather",
  "display_name": "Weather API",
  "description": "Get current weather for a city",
  "plugin_type": "http",
  "config": {
    "url": "https://wttr.in/{city}?format=3",
    "method": "GET",
    "headers": {},
    "body_template": ""
  },
  "parameters": {
    "type": "object",
    "properties": {
      "city": {"type": "string", "description": "City name"}
    },
    "required": ["city"]
  }
}

Placeholders {param_name} in url/body/headers are filled from skill arguments.
"""

import re
import json
from app.plugins.base_plugin import BasePlugin


class HTTPPlugin(BasePlugin):
    plugin_type = "http"
    config_schema = {
        "url":          {"type": "string", "description": "Endpoint URL, use {param} for placeholders"},
        "method":       {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
        "headers":      {"type": "object", "description": "HTTP headers, use {param} for values"},
        "body_template":{"type": "string", "description": "JSON body template with {param} placeholders"},
    }

    def __init__(self, spec: dict):
        self.name        = spec["name"]
        self.description = spec.get("description", f"HTTP plugin: {spec['name']}")
        self.parameters  = spec.get("parameters", {"type": "object", "properties": {}})
        self.config      = spec.get("config", {})

    def _fill(self, template: str, args: dict) -> str:
        """Replace {key} placeholders with args values."""
        for k, v in args.items():
            template = template.replace(f"{{{k}}}", str(v))
        return template

    async def execute(self, **kwargs) -> str:
        import aiohttp
        cfg = self.config
        method  = cfg.get("method", "GET").upper()
        url     = self._fill(cfg.get("url", ""), kwargs)
        headers = {k: self._fill(v, kwargs) for k, v in cfg.get("headers", {}).items()}
        body    = None

        body_tmpl = cfg.get("body_template", "")
        if body_tmpl:
            filled = self._fill(body_tmpl, kwargs)
            try:
                body = json.loads(filled)
            except Exception:
                body = filled

        try:
            async with aiohttp.ClientSession() as s:
                req_kwargs = {"headers": headers, "timeout": aiohttp.ClientTimeout(total=15)}
                if body and method in ("POST", "PUT"):
                    req_kwargs["json" if isinstance(body, dict) else "data"] = body
                async with s.request(method, url, **req_kwargs) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        return f"HTTP {resp.status}: {text[:300]}"
                    # Try to pretty-print JSON
                    try:
                        return json.dumps(json.loads(text), indent=2)[:2000]
                    except Exception:
                        return text[:2000]
        except Exception as e:
            return f"HTTP plugin error: {e}"
