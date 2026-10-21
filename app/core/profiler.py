"""Apple Silicon Unified Memory (RSS + Metal) profiler and hardware watchdog."""

import asyncio
import collections
import importlib
import logging
import time
from collections.abc import Callable
from typing import Any, NamedTuple

import psutil

from app.config import settings

logger = logging.getLogger("app.core.profiler")

# Try to import MLX Metal memory bindings if on Apple Silicon with MLX installed
mx: Any = None
try:
    mx = importlib.import_module("mlx.core")
    HAS_MLX = True
except (ImportError, AttributeError):
    mx = None
    HAS_MLX = False


class MemorySnapshot(NamedTuple):
    timestamp_ns: int
    rss_bytes: int
    metal_bytes: int
    rss_gb: float
    metal_gb: float
    total_unified_gb: float
    warning_triggered: bool
    ceiling_triggered: bool


class HardwareProfiler:
    """Samples Unified RAM (Process RSS + Metal buffers) at 20 ms and enforces hardware ceilings."""

    def __init__(
        self,
        warning_gb: float = settings.MEMORY_WARNING_GB,
        ceiling_gb: float = settings.MEMORY_CEILING_GB,
        sample_interval_ms: int = settings.PROFILER_INTERVAL_MS,
        ring_buffer_size: int = 1000,
    ) -> None:
        self.warning_gb = warning_gb
        self.ceiling_gb = ceiling_gb
        self.interval_s = sample_interval_ms / 1000.0
        self._process = psutil.Process()
        self._ring_buffer: collections.deque[MemorySnapshot] = collections.deque(maxlen=ring_buffer_size)
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._warning_callback: Callable[[MemorySnapshot], None] | None = None
        self._ceiling_callback: Callable[[MemorySnapshot], None] | None = None
        self._simulated_rss_bytes: int | None = None
        self._simulated_metal_bytes: int | None = None

    def set_warning_callback(self, cb: Callable[[MemorySnapshot], None]) -> None:
        self._warning_callback = cb

    def set_ceiling_callback(self, cb: Callable[[MemorySnapshot], None]) -> None:
        self._ceiling_callback = cb

    def set_simulated_memory(self, rss_bytes: int | None, metal_bytes: int | None) -> None:
        """Testing hook to verify tripwire triggers without actual physical memory exhaustion."""
        self._simulated_rss_bytes = rss_bytes
        self._simulated_metal_bytes = metal_bytes

    def get_metal_active_memory(self) -> int:
        """Return active Apple Metal buffer bytes."""
        if self._simulated_metal_bytes is not None:
            return self._simulated_metal_bytes
        if HAS_MLX and mx is not None:
            try:
                return int(mx.metal.get_active_memory())
            except Exception:
                pass
        return 0

    def sample_now(self) -> MemorySnapshot:
        """Synchronously sample process RSS and Metal buffers."""
        now_ns = time.perf_counter_ns()
        if self._simulated_rss_bytes is not None:
            rss_bytes = self._simulated_rss_bytes
        else:
            try:
                rss_bytes = self._process.memory_info().rss
            except Exception:
                rss_bytes = 0

        metal_bytes = self.get_metal_active_memory()
        rss_gb = rss_bytes / (1024**3)
        metal_gb = metal_bytes / (1024**3)
        total_unified_gb = rss_gb + metal_gb

        warn_flag = total_unified_gb >= self.warning_gb
        abort_flag = total_unified_gb >= self.ceiling_gb

        snap = MemorySnapshot(
            timestamp_ns=now_ns,
            rss_bytes=rss_bytes,
            metal_bytes=metal_bytes,
            rss_gb=rss_gb,
            metal_gb=metal_gb,
            total_unified_gb=total_unified_gb,
            warning_triggered=warn_flag,
            ceiling_triggered=abort_flag,
        )
        self._ring_buffer.append(snap)

        if abort_flag:
            logger.critical(
                f"HARD ENGINE CEILING BREACH: Unified RAM at {total_unified_gb:.2f} GB "
                f"(Ceiling: {self.ceiling_gb:.2f} GB). Triggering cache clear & emergency abort."
            )
            self.clear_metal_cache()
            if self._ceiling_callback:
                self._ceiling_callback(snap)
        elif warn_flag:
            logger.warning(
                f"MEMORY TRIPWIRE WARNING: Unified RAM at {total_unified_gb:.2f} GB "
                f"(Warning tripwire: {self.warning_gb:.2f} GB)."
            )
            if self._warning_callback:
                self._warning_callback(snap)

        return snap

    def clear_metal_cache(self) -> None:
        """Clear Metal buffer caches on Apple Silicon."""
        if HAS_MLX and mx is not None:
            try:
                mx.metal.clear_cache()
                logger.info("Executed mlx.core.metal.clear_cache()")
            except Exception as exc:
                logger.error(f"Failed clearing MLX cache: {exc}")

    async def _loop(self) -> None:
        while self._running:
            self.sample_now()
            await asyncio.sleep(self.interval_s)

    def start(self) -> None:
        """Start background 20 ms sampling loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop(), name="HardwareProfilerWatchdog")

    async def stop(self) -> None:
        """Stop background sampling loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    @property
    def latest_sample(self) -> MemorySnapshot | None:
        return self._ring_buffer[-1] if self._ring_buffer else None

    @property
    def recent_samples(self) -> list[MemorySnapshot]:
        return list(self._ring_buffer)


profiler = HardwareProfiler()
