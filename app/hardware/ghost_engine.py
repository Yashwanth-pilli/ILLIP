"""
Ghost GPU Engine — auto-calculates optimal model loading for any hardware.

Problem: Big model + small GPU = crash or slow.
Solution: Split layers between GPU/CPU, quantize, offload KV cache.

Works on any laptop. Students with 4GB GPU can run 7B.
Students with 8GB GPU can run 13-14B.
Students with 16GB RAM only (no GPU) can run 7B on CPU.
"""

from dataclasses import dataclass, field
from typing import Optional
from app.hardware.detector import get_hardware_info
from app.utils import logger

# Model size database (VRAM needed for full GPU load, Q4_K_M quantized)
# format: {model_name: (param_billions, vram_gb_q4, layers)}
_MODEL_DB: dict[str, tuple[float, float, int]] = {
    "qwen2.5:1.5b":  (1.5,  1.1,  28),
    "qwen2.5:3b":    (3.0,  2.0,  36),
    "qwen2.5:7b":    (7.0,  4.7,  28),
    "qwen2.5:14b":   (14.0, 9.0,  48),
    "qwen2.5:32b":   (32.0, 20.0, 64),
    "qwen2.5:72b":   (72.0, 43.0, 80),
    "llama3.1:8b":   (8.0,  5.0,  32),
    "llama3.1:70b":  (70.0, 40.0, 80),
    "mistral:7b":    (7.0,  4.1,  32),
    "phi3:mini":     (3.8,  2.3,  32),
    "phi3:medium":   (14.0, 8.5,  40),
    "gemma2:2b":     (2.0,  1.6,  26),
    "gemma2:9b":     (9.0,  5.5,  42),
    "gemma2:27b":    (27.0, 16.0, 46),
}

# Safety buffer: keep this much VRAM free for OS + driver overhead
_VRAM_SAFETY_GB = 1.2
_RAM_SAFETY_GB  = 2.0


@dataclass
class GhostPlan:
    model: str
    gpu_layers: int          # layers loaded to GPU
    cpu_layers: int          # layers offloaded to CPU RAM
    total_layers: int
    vram_used_gb: float
    ram_used_gb: float
    use_kv_offload: bool     # offload KV cache to CPU between tokens
    use_mmap: bool           # memory-map weights (OS pages on demand)
    use_mlock: bool          # lock weights in RAM (no swap thrashing)
    threads: int             # CPU threads for CPU layers
    context_limit: int       # safe context given available memory
    strategy: str            # "full_gpu" | "hybrid" | "cpu_only"
    feasible: bool
    warnings: list[str] = field(default_factory=list)
    ollama_options: dict = field(default_factory=dict)


async def _fetch_model_info(model: str, base_url: str = "http://localhost:11434") -> tuple[float, float, int] | None:
    """
    Ask Ollama for real model architecture info.
    Returns (param_billions, vram_q4_gb, num_layers) or None if unavailable.
    """
    try:
        import aiohttp, re
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{base_url}/api/show",
                json={"name": model},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        details = data.get("details", {})
        param_str = details.get("parameter_size", "")   # e.g. "7B", "70.6B"
        quant     = details.get("quantization_level", "Q4_K_M")

        # Parse param count
        m = re.search(r"([\d.]+)\s*[Bb]", param_str)
        if not m:
            return None
        param_b = float(m.group(1))

        # Bits per param from quantization
        quant_bits = {
            "Q2_K": 2.5, "Q3_K_S": 3.0, "Q3_K_M": 3.35, "Q3_K_L": 3.5,
            "Q4_0": 4.0, "Q4_K_S": 4.0, "Q4_K_M": 4.5, "Q5_K_M": 5.5,
            "Q6_K": 6.0, "Q8_0": 8.0, "F16": 16.0, "F32": 32.0,
        }.get(quant, 4.5)

        vram_gb = round(param_b * quant_bits / 8 * 1.1, 2)   # +10% overhead

        # Estimate layers from param count (standard transformer scaling)
        layers = max(16, int(param_b * 1.1))

        # Try to get exact layer count from modelinfo
        info = data.get("model_info", {})
        for key in info:
            if "num_hidden_layers" in key or "n_layer" in key:
                try:
                    layers = int(info[key])
                    break
                except Exception:
                    pass

        return (param_b, vram_gb, layers)
    except Exception:
        return None


def calculate_plan(model: str, requested_ctx: int = 8192) -> GhostPlan:
    """
    Given a model name and desired context, return the optimal loading plan
    for the current hardware. Works for any laptop — degrades gracefully.
    """
    hw = get_hardware_info()
    info = _MODEL_DB.get(model)
    warnings = []

    if info is None:
        # Unknown model — estimate from name (sync fallback, Ollama not queried here)
        param_b = _guess_params(model)
        vram_q4 = param_b * 0.67   # rough Q4_K_M estimate
        total_layers = max(28, int(param_b * 1.1))
        info = (param_b, vram_q4, total_layers)
        warnings.append(
            f"Model '{model}' not in local DB — using parameter estimates. "
            "Accuracy improves when Ollama is running (live query via /api/show)."
        )

    param_b, vram_needed_gb, total_layers = info
    avail_vram = max(0.0, hw.gpu_vram_gb - _VRAM_SAFETY_GB)
    avail_ram  = max(0.0, hw.ram_available_gb - _RAM_SAFETY_GB)

    # Context window costs VRAM/RAM for KV cache
    # Rough estimate: 0.5MB per token per layer for 7B, scales with params
    ctx_vram_gb = (requested_ctx * total_layers * 0.0000005 * (param_b / 7.0))

    # Strategy 1: Full GPU
    if vram_needed_gb + ctx_vram_gb <= avail_vram:
        gpu_layers = total_layers
        cpu_layers = 0
        strategy = "full_gpu"
        vram_used = vram_needed_gb + ctx_vram_gb
        ram_used = 0.1
        kv_offload = False
        context = requested_ctx

    # Strategy 2: KV cache offload to CPU (saves VRAM, model still fits)
    elif vram_needed_gb <= avail_vram:
        gpu_layers = total_layers
        cpu_layers = 0
        strategy = "full_gpu_kv_offload"
        vram_used = vram_needed_gb
        ram_used = ctx_vram_gb
        kv_offload = True
        context = min(requested_ctx, int(avail_ram / (ctx_vram_gb / max(requested_ctx, 1)) * 1024))
        warnings.append("KV cache offloaded to CPU RAM. Slightly slower but fits in VRAM.")

    # Strategy 3: Hybrid split — some layers GPU, rest CPU
    elif avail_vram > 0.5:
        vram_per_layer = vram_needed_gb / total_layers
        gpu_layers = max(1, int(avail_vram / vram_per_layer))
        cpu_layers = total_layers - gpu_layers
        strategy = "hybrid"
        vram_used = gpu_layers * vram_per_layer
        ram_per_layer = vram_needed_gb / total_layers
        ram_used = cpu_layers * ram_per_layer + ctx_vram_gb
        kv_offload = True

        if ram_used > avail_ram:
            # Reduce context to fit
            ctx_budget = max(0, avail_ram - cpu_layers * ram_per_layer)
            context = max(512, int(ctx_budget / (ctx_vram_gb / max(requested_ctx, 1))))
            warnings.append(
                f"RAM tight — context reduced to {context} tokens. "
                "Close other apps for more capacity."
            )
        else:
            context = requested_ctx

        gpu_pct = int(gpu_layers / total_layers * 100)
        warnings.append(
            f"Hybrid mode: {gpu_pct}% of layers on GPU, rest on CPU. "
            "Expect ~2-4x slower than full GPU. Still works."
        )

    # Strategy 4: CPU only
    else:
        gpu_layers = 0
        cpu_layers = total_layers
        strategy = "cpu_only"
        vram_used = 0.0
        ram_used = vram_needed_gb + ctx_vram_gb
        kv_offload = False
        context = min(requested_ctx, 2048)
        warnings.append(
            "No GPU available or VRAM too small. Running on CPU. "
            "Expect slow responses. Consider a smaller model."
        )

    feasible = ram_used <= (hw.ram_gb - _RAM_SAFETY_GB) or strategy in ("full_gpu", "full_gpu_kv_offload")
    if not feasible:
        warnings.append(
            f"WARNING: Not enough RAM ({hw.ram_gb}GB) for {model}. "
            f"Need ~{ram_used:.1f}GB. Use a smaller/more quantized model."
        )

    safe_threads = max(2, (hw.cpu_cores or 4) - 2)

    # Build Ollama options dict — pass directly to /api/chat
    ollama_options = {
        "num_gpu":     gpu_layers,     # layers on GPU (0 = CPU only)
        "num_thread":  safe_threads,   # CPU threads
        "num_ctx":     context,        # context window
        "use_mmap":    True,           # memory-mapped weights (OS pages on demand)
        "use_mlock":   strategy in ("full_gpu", "cpu_only"),  # lock if fits
    }

    plan = GhostPlan(
        model=model,
        gpu_layers=gpu_layers,
        cpu_layers=cpu_layers,
        total_layers=total_layers,
        vram_used_gb=round(vram_used, 2),
        ram_used_gb=round(ram_used, 2),
        use_kv_offload=kv_offload,
        use_mmap=True,
        use_mlock=ollama_options["use_mlock"],
        threads=safe_threads,
        context_limit=context,
        strategy=strategy,
        feasible=feasible,
        warnings=warnings,
        ollama_options=ollama_options,
    )

    logger.info(
        f"GhostEngine: {model} | strategy={strategy} | "
        f"gpu_layers={gpu_layers}/{total_layers} | "
        f"VRAM={vram_used:.1f}GB | RAM={ram_used:.1f}GB | ctx={context}"
    )
    return plan


async def calculate_plan_async(model: str, requested_ctx: int = 8192, base_url: str = "http://localhost:11434") -> GhostPlan:
    """
    Like calculate_plan() but queries Ollama /api/show for real architecture.
    Use this for any model not in _MODEL_DB. Falls back to sync estimate if Ollama unreachable.
    """
    live_info = await _fetch_model_info(model, base_url)
    if live_info is not None:
        param_b, vram_gb, num_layers = live_info
        # Temporarily inject into DB so calculate_plan() picks it up
        _MODEL_DB[model] = (param_b, vram_gb, num_layers)
    return calculate_plan(model, requested_ctx)


def _guess_params(model_name: str) -> float:
    """Estimate param count from model name string."""
    import re
    m = re.search(r'(\d+(?:\.\d+)?)\s*[bB]', model_name)
    if m:
        return float(m.group(1))
    return 7.0  # default guess


def recommend_model_for_hardware() -> str:
    """Pick the best model the hardware can run at full quality."""
    hw = get_hardware_info()
    avail_vram = max(0.0, hw.gpu_vram_gb - _VRAM_SAFETY_GB)
    avail_ram  = max(0.0, hw.ram_available_gb - _RAM_SAFETY_GB)

    # Prefer fitting entirely in VRAM for best speed
    candidates = [
        ("qwen2.5:72b", 43.0),
        ("qwen2.5:32b", 20.0),
        ("qwen2.5:14b", 9.0),
        ("qwen2.5:7b",  4.7),
        ("qwen2.5:3b",  2.0),
        ("qwen2.5:1.5b", 1.1),
    ]
    for name, vram_needed in candidates:
        if vram_needed <= avail_vram:
            return name

    # Nothing fits in VRAM — pick what fits in RAM for CPU/hybrid
    for name, vram_needed in candidates:
        if vram_needed <= avail_ram:
            return name

    return "qwen2.5:1.5b"
