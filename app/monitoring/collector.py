"""
Metrics collector — system + ILLIP runtime observability.

Requires: psutil (pip install psutil)
Optional: nvidia-smi on PATH for GPU metrics
"""

import asyncio
import subprocess
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from app.utils import logger


class MetricsCollector:
    def __init__(self, interval: int = 10, history_size: int = 60):
        self._interval = interval
        self._history: deque[dict] = deque(maxlen=history_size)
        self._task: Optional[asyncio.Task] = None
        self._running = False

        # Runtime counters
        self.agent_calls: dict[str, int] = {}
        self.skill_calls: dict[str, int] = {}
        self.chat_count: int = 0
        self.error_count: int = 0
        self.startup_time: str = datetime.now(timezone.utc).isoformat()

    # ── recording ──────────────────────────────────────────────────────────

    def record_agent_call(self, agent_type: str) -> None:
        self.agent_calls[agent_type] = self.agent_calls.get(agent_type, 0) + 1

    def record_skill_call(self, skill_name: str) -> None:
        self.skill_calls[skill_name] = self.skill_calls.get(skill_name, 0) + 1

    def record_chat(self) -> None:
        self.chat_count += 1

    def record_error(self) -> None:
        self.error_count += 1

    # ── collection ─────────────────────────────────────────────────────────

    def _collect_gpu(self) -> Optional[dict]:
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                timeout=3, stderr=subprocess.DEVNULL,
            ).decode().strip()
            parts = [p.strip() for p in out.split(",")]
            if len(parts) == 3:
                return {
                    "utilization_pct": float(parts[0]),
                    "memory_used_mb": float(parts[1]),
                    "memory_total_mb": float(parts[2]),
                }
        except Exception:
            pass
        return None

    def _snapshot(self) -> dict:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            sys_metrics = {
                "cpu_pct": cpu,
                "ram_used_mb": round(ram.used / 1024 / 1024, 1),
                "ram_total_mb": round(ram.total / 1024 / 1024, 1),
                "ram_pct": ram.percent,
                "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "disk_pct": disk.percent,
            }
        except ImportError:
            sys_metrics = {"error": "psutil not installed"}

        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "system": sys_metrics,
            "gpu": self._collect_gpu(),
            "runtime": {
                "chat_count": self.chat_count,
                "error_count": self.error_count,
                "agent_calls_total": sum(self.agent_calls.values()),
                "skill_calls_total": sum(self.skill_calls.values()),
            },
        }

    # ── lifecycle ──────────────────────────────────────────────────────────

    async def _loop(self) -> None:
        try:
            import psutil
            psutil.cpu_percent(interval=None)  # prime the first reading
        except ImportError:
            pass
        while self._running:
            try:
                snap = self._snapshot()
                self._history.append(snap)
            except Exception as e:
                logger.debug(f"Metrics collect error: {e}")
            await asyncio.sleep(self._interval)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Metrics collector started")

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    # ── query ──────────────────────────────────────────────────────────────

    def get_current(self) -> dict:
        return self._snapshot()

    def get_history(self) -> list:
        return list(self._history)

    def get_summary(self) -> dict:
        now = datetime.now(timezone.utc)
        startup = datetime.fromisoformat(self.startup_time)
        uptime_s = int((now - startup).total_seconds())

        history = list(self._history)
        avg_cpu = (
            round(sum(h["system"].get("cpu_pct", 0) for h in history) / len(history), 1)
            if history else 0.0
        )
        avg_ram = (
            round(sum(h["system"].get("ram_pct", 0) for h in history) / len(history), 1)
            if history else 0.0
        )

        return {
            "startup_time": self.startup_time,
            "uptime_seconds": uptime_s,
            "uptime_human": f"{uptime_s // 3600}h {(uptime_s % 3600) // 60}m",
            "chat_count": self.chat_count,
            "error_count": self.error_count,
            "agent_calls": self.agent_calls,
            "skill_calls": self.skill_calls,
            "avg_cpu_pct": avg_cpu,
            "avg_ram_pct": avg_ram,
            "history_points": len(history),
        }


_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
