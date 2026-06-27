"""
Ghost GPU Safety Monitor — background watcher.

Runs as asyncio task. Checks GPU temp + VRAM every 5s.
Emits warnings. Reduces active context on high pressure.
Never kills the process — just signals the engine to back off.
"""

import asyncio
from app.utils import logger

_POLL_INTERVAL = 5     # seconds between checks
_TEMP_WARN     = 75    # °C — log warning
_TEMP_CRITICAL = 83    # °C — reduce context, log critical
_VRAM_WARN     = 85    # % — log warning
_VRAM_CRITICAL = 93    # % — log critical

# Global signal — read by OllamaProvider to throttle
_pressure_signal: str = "low"    # low | medium | high | critical


def get_pressure() -> str:
    return _pressure_signal


def _assess(state) -> str:
    if state.gpu_temp_c >= _TEMP_CRITICAL or state.vram_percent >= _VRAM_CRITICAL:
        return "critical"
    if state.gpu_temp_c >= _TEMP_WARN or state.vram_percent >= _VRAM_WARN:
        return "high"
    if state.ram_percent >= 85 or state.cpu_percent >= 90:
        return "medium"
    return "low"


async def _monitor_loop():
    global _pressure_signal
    from app.hardware.guard import read_hardware_state_async
    while True:
        try:
            state    = await read_hardware_state_async()
            pressure = _assess(state)
            if pressure != _pressure_signal:
                logger.warning(
                    f"SafetyMonitor: pressure {_pressure_signal}→{pressure} | "
                    f"GPU {state.gpu_temp_c:.0f}°C {state.vram_percent:.0f}%VRAM "
                    f"RAM {state.ram_percent:.0f}%"
                )
            _pressure_signal = pressure

            if pressure == "critical":
                logger.error(
                    f"SafetyMonitor: CRITICAL — GPU {state.gpu_temp_c}°C / "
                    f"VRAM {state.vram_percent:.0f}%. "
                    "New requests will use reduced context until pressure drops."
                )
        except Exception as e:
            logger.debug(f"SafetyMonitor read error (non-critical): {e}")

        await asyncio.sleep(_POLL_INTERVAL)


_monitor_task: asyncio.Task | None = None


def start_monitor():
    """Start background monitor. Call once from app startup. Safe to call multiple times."""
    global _monitor_task
    if _monitor_task is not None and not _monitor_task.done():
        return
    try:
        loop = asyncio.get_event_loop()
        _monitor_task = loop.create_task(_monitor_loop())
        logger.info("SafetyMonitor: started (5s GPU/RAM polling)")
    except RuntimeError:
        logger.debug("SafetyMonitor: no event loop yet — will start on first request")


def stop_monitor():
    global _monitor_task
    if _monitor_task:
        _monitor_task.cancel()
        _monitor_task = None
