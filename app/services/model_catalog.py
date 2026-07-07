"""
Curated model catalog — "which model should I download for MY machine?"

The built-in list covers the practical sweet spots from 4GB CPU-only laptops
up to 16GB+ GPUs. Users can replace/extend it by dropping a JSON file at
data/model_catalog.json with the same shape — nothing hardcoded.

Fit verdicts are catalog-driven (min_vram/min_ram) rather than ghost-engine
plans because the ghost engine needs the model installed to inspect it;
this answers "will it fit BEFORE I download 5GB".
"""

import json
import os
import shutil
from pathlib import Path

from app.utils import logger

# Download size ≈ Ollama default quant (Q4_K_M). min_vram_gb = comfortable
# full-GPU. min_ram_gb = usable hybrid/CPU floor.
DEFAULT_CATALOG = [
    {"name": "llama3.2:1b", "size_gb": 1.3, "min_vram_gb": 2, "min_ram_gb": 4,
     "blurb": "Tiny and snappy — runs on almost anything, even without a GPU.",
     "good_for": ["chat"], "tier": "low"},
    {"name": "llama3.2:3b", "size_gb": 2.0, "min_vram_gb": 3, "min_ram_gb": 6,
     "blurb": "Best micro all-rounder. The safe pick for older laptops.",
     "good_for": ["chat"], "tier": "low"},
    {"name": "gemma3:4b", "size_gb": 3.3, "min_vram_gb": 4, "min_ram_gb": 8,
     "blurb": "Google's small model — also understands images.",
     "good_for": ["chat", "vision"], "tier": "low"},
    {"name": "qwen2.5:7b", "size_gb": 4.7, "min_vram_gb": 6, "min_ram_gb": 12,
     "blurb": "Great everyday all-rounder for chat and light coding.",
     "good_for": ["chat", "coding"], "tier": "mid"},
    {"name": "qwen2.5-coder:7b", "size_gb": 4.7, "min_vram_gb": 6, "min_ram_gb": 12,
     "blurb": "Coding specialist — better at code than same-size chat models.",
     "good_for": ["coding"], "tier": "mid"},
    {"name": "llama3.1:8b", "size_gb": 4.9, "min_vram_gb": 6, "min_ram_gb": 12,
     "blurb": "Meta's classic 8B — strong general assistant.",
     "good_for": ["chat"], "tier": "mid"},
    {"name": "deepseek-r1:8b", "size_gb": 5.2, "min_vram_gb": 7, "min_ram_gb": 12,
     "blurb": "Reasoning model — thinks step-by-step before answering.",
     "good_for": ["reasoning"], "tier": "mid"},
    {"name": "hermes3:8b", "size_gb": 4.7, "min_vram_gb": 6, "min_ram_gb": 12,
     "blurb": "Nous Hermes — steerable, follows YOUR persona/rules closely. 128K context.",
     "good_for": ["chat", "roleplay"], "tier": "mid"},
    {"name": "gemma3:12b", "size_gb": 8.1, "min_vram_gb": 10, "min_ram_gb": 16,
     "blurb": "Strong mid-size model with vision. Needs a real GPU.",
     "good_for": ["chat", "vision"], "tier": "high"},
    {"name": "phi4:14b", "size_gb": 9.1, "min_vram_gb": 11, "min_ram_gb": 16,
     "blurb": "Microsoft's 14B — strong logic and math.",
     "good_for": ["reasoning"], "tier": "high"},
    {"name": "gpt-oss:20b", "size_gb": 13.0, "min_vram_gb": 16, "min_ram_gb": 20,
     "blurb": "OpenAI's open MoE — heavy 'deep think'. Runs hybrid on 8GB GPU + 16GB RAM.",
     "good_for": ["reasoning"], "tier": "high"},
    {"name": "nomic-embed-text", "size_gb": 0.28, "min_vram_gb": 0, "min_ram_gb": 2,
     "blurb": "Embedding model — powers ILLIP's long-term memory search.",
     "good_for": ["embeddings"], "tier": "low"},
]

_OVERRIDE_FILE = Path("data/model_catalog.json")


def load_catalog() -> list[dict]:
    """Built-in catalog, replaced by data/model_catalog.json when present."""
    if _OVERRIDE_FILE.exists():
        try:
            user = json.loads(_OVERRIDE_FILE.read_text(encoding="utf-8"))
            if isinstance(user, list) and user:
                return user
        except Exception as e:
            logger.warning(f"model_catalog.json invalid, using built-in: {e}")
    return DEFAULT_CATALOG


def fit_verdict(entry: dict, vram_gb: float, ram_gb: float) -> str:
    """full-gpu | partial | cpu | too-big for this machine.
    +1GB RAM tolerance: a nominal 16GB machine reports ~15.3GB usable and
    must not get 'too-big' for a model that measurably runs on it."""
    ram = ram_gb + 1
    if vram_gb >= entry.get("min_vram_gb", 0):
        return "full-gpu"
    if vram_gb >= 4 and ram >= entry.get("min_ram_gb", 0):
        return "partial"
    if ram >= entry.get("min_ram_gb", 0):
        return "cpu"
    return "too-big"


def ollama_models_dir() -> Path:
    env = os.environ.get("OLLAMA_MODELS", "").strip()
    if env:
        return Path(env)
    return Path.home() / ".ollama" / "models"


def free_disk_gb(path: Path | None = None) -> float:
    """Free space on the drive where Ollama stores models."""
    p = path or ollama_models_dir()
    while not p.exists() and p.parent != p:
        p = p.parent
    try:
        return shutil.disk_usage(p).free / 1024**3
    except OSError:
        return 0.0


def disk_ok(size_gb: float, free_gb: float | None = None) -> tuple[bool, float]:
    """1.2x margin — Ollama unpacks layers while pulling."""
    free = free_disk_gb() if free_gb is None else free_gb
    return free >= size_gb * 1.2, round(free, 1)


def recommend_download(catalog: list[dict], installed: set[str],
                       vram_gb: float, ram_gb: float) -> str | None:
    """Largest chat-capable model that fits fully on GPU; else largest partial
    fit; else the tiny one. Smallest-useful-first for weak machines comes free:
    on 0 VRAM nothing is full-gpu, so the CPU-capable tiny models win."""
    chat = [e for e in catalog if "chat" in e.get("good_for", []) and e["name"] not in installed]
    for want in ("full-gpu", "partial", "cpu"):
        best = None
        for e in chat:
            if fit_verdict(e, vram_gb, ram_gb) == want:
                if best is None or e["size_gb"] > best["size_gb"]:
                    best = e
        if best:
            return best["name"]
    return None
