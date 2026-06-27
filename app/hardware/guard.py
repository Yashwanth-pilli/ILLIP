"""
Hardware guard — reads live CPU/RAM/GPU/temp and enforces safety thresholds.
All reads are non-blocking; failures return safe defaults.
"""

import subprocess
import asyncio
from dataclasses import dataclass
from typing import Optional
from app.utils import logger

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


@dataclass
class HardwareState:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    gpu_vram_used_mb: float = 0.0
    gpu_vram_total_mb: float = 8192.0
    gpu_temp_c: float = 0.0
    gpu_util_percent: float = 0.0
    # derived
    vram_percent: float = 0.0
    is_safe: bool = True
    pressure: str = "low"   # low / medium / high / critical
    recommended_model: Optional[str] = None
    reason: str = ""


# Thresholds
_TEMP_WARN  = 75   # °C — switch to small model
_TEMP_LIMIT = 82   # °C — critical, drop context
_VRAM_WARN  = 80   # % — switch to small model
_VRAM_LIMIT = 92   # % — critical
_RAM_WARN   = 85   # %
_CPU_WARN   = 90   # %


def _nvidia_smi_query(fields: str) -> Optional[list[str]]:
    """Run nvidia-smi with given comma-separated fields, return values list."""
    try:
        result = subprocess.run(
            ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [v.strip() for v in result.stdout.strip().split(",")]
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.debug(f"nvidia-smi failed: {e}")
    return None


def read_hardware_state() -> HardwareState:
    s = HardwareState()

    # CPU + RAM
    if _PSUTIL:
        try:
            s.cpu_percent = psutil.cpu_percent(interval=0.1)
            vm = psutil.virtual_memory()
            s.ram_percent = vm.percent
        except Exception:
            pass

    # GPU via nvidia-smi
    vals = _nvidia_smi_query(
        "temperature.gpu,memory.used,memory.total,utilization.gpu"
    )
    if vals and len(vals) == 4:
        try:
            s.gpu_temp_c        = float(vals[0])
            s.gpu_vram_used_mb  = float(vals[1])
            s.gpu_vram_total_mb = float(vals[2])
            s.gpu_util_percent  = float(vals[3])
            s.vram_percent = (s.gpu_vram_used_mb / s.gpu_vram_total_mb * 100) if s.gpu_vram_total_mb else 0
        except ValueError:
            pass

    # Determine pressure level
    if s.gpu_temp_c >= _TEMP_LIMIT or s.vram_percent >= _VRAM_LIMIT:
        s.pressure = "critical"
        s.is_safe  = False
        s.reason   = f"GPU temp {s.gpu_temp_c}°C / VRAM {s.vram_percent:.0f}%"
    elif s.gpu_temp_c >= _TEMP_WARN or s.vram_percent >= _VRAM_WARN or s.ram_percent >= _RAM_WARN:
        s.pressure = "high"
        s.reason   = f"GPU temp {s.gpu_temp_c}°C / VRAM {s.vram_percent:.0f}%"
    elif s.cpu_percent >= _CPU_WARN:
        s.pressure = "medium"
        s.reason   = f"CPU {s.cpu_percent:.0f}%"
    else:
        s.pressure = "low"

    return s


_hw_cache: HardwareState | None = None
_hw_cache_ts: float = 0.0
_HW_CACHE_TTL = 10.0   # seconds; hardware changes slowly, no need to query nvidia-smi per-request


async def read_hardware_state_async() -> HardwareState:
    """Non-blocking version with 10s cache — nvidia-smi takes 1-3s per call on Windows."""
    global _hw_cache, _hw_cache_ts
    import time
    now = time.monotonic()
    if _hw_cache is not None and (now - _hw_cache_ts) < _HW_CACHE_TTL:
        return _hw_cache
    loop = asyncio.get_event_loop()
    state = await loop.run_in_executor(None, read_hardware_state)
    _hw_cache = state
    _hw_cache_ts = now
    return state


def get_safe_context_limit(state: HardwareState, requested: int = 8192) -> int:
    """Return a safe num_ctx given hardware pressure."""
    if state.pressure == "critical":
        return min(requested, 2048)
    if state.pressure == "high":
        return min(requested, 4096)
    return requested
