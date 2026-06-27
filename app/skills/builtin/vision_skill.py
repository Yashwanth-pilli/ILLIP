"""
Vision skill — describe / analyze images using a local multimodal model (LLaVA family).
Passes base64-encoded image to Ollama /api/generate with the model's vision support.
"""

import base64
from app.skills.base_skill import BaseSKill
from app.utils import logger

_VISION_FAMILIES = ["llava-phi3", "llava", "llava:7b", "llava:13b", "moondream", "minicpm-v", "bakllava"]


async def _detect_vision_model(base_url: str) -> str | None:
    """Return first installed vision model, or None."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status != 200:
                    return None
                d = await r.json()
                installed = {m["name"] for m in d.get("models", [])}
        for fam in _VISION_FAMILIES:
            for name in installed:
                if name.startswith(fam.split(":")[0]):
                    return name
    except Exception:
        pass
    return None


async def analyze_image(
    image_bytes: bytes,
    prompt: str = "Describe this image in detail.",
    base_url: str = "http://localhost:11434",
) -> str:
    """Send image bytes to vision model, return description."""
    model = await _detect_vision_model(base_url)
    if not model:
        return "No vision model installed. Run: ollama pull llava-phi3"

    b64 = base64.b64encode(image_bytes).decode()
    try:
        import aiohttp
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 512},
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    return f"Vision model error {resp.status}"
                d = await resp.json()
                return d.get("response", "").strip() or "No description generated."
    except Exception as e:
        logger.error(f"Vision analyze error: {e}")
        return f"Vision error: {e}"


class VisionSkill(BaseSKill):
    name = "vision_analyze"
    description = (
        "Analyze or describe an image. Use when user sends a photo or asks about image content. "
        "Provide the image as base64 string."
    )
    parameters = {
        "type": "object",
        "properties": {
            "image_base64": {
                "type": "string",
                "description": "Base64-encoded image bytes",
            },
            "prompt": {
                "type": "string",
                "description": "What to ask about the image. Default: describe it.",
            },
        },
        "required": ["image_base64"],
    }

    async def execute(self, image_base64: str, prompt: str = "Describe this image in detail.", **_) -> str:
        from app.config import settings
        image_bytes = base64.b64decode(image_base64)
        return await analyze_image(image_bytes, prompt, settings.ollama_base_url)
