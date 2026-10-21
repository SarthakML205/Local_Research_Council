"""Asyncio task dispatcher with bounded semaphores and low-latency dispatch."""

import asyncio
import collections
import logging
import time
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger("app.core.engine")

T = TypeVar("T")


class AsyncEngine:
    """Task dispatcher managing bounded concurrency pools and measuring dispatch latency."""

    def __init__(
        self,
        io_concurrency: int = 16,
        inference_concurrency: int = 1,
        latency_history_size: int = 1000,
    ) -> None:
        self.io_semaphore = asyncio.Semaphore(io_concurrency)
        self.inference_semaphore = asyncio.Semaphore(inference_concurrency)
        self._active_tasks: set[asyncio.Task[Any]] = set()
        self._dispatch_latencies_ns: collections.deque[int] = collections.deque(maxlen=latency_history_size)
        self._lock = asyncio.Lock()

    async def run_io_bounded(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run an I/O task gated by the I/O semaphore."""
        t_start = time.perf_counter_ns()
        async with self.io_semaphore:
            dispatch_ns = time.perf_counter_ns() - t_start
            self._dispatch_latencies_ns.append(dispatch_ns)
            return await coro

    async def run_inference_bounded(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run a single-LLM inference task gated by the engine semaphore."""
        t_start = time.perf_counter_ns()
        async with self.inference_semaphore:
            dispatch_ns = time.perf_counter_ns() - t_start
            self._dispatch_latencies_ns.append(dispatch_ns)
            return await coro

    def spawn_background(
        self,
        coro: Coroutine[Any, Any, Any],
        name: str = "lrc-bg-task",
    ) -> asyncio.Task[Any]:
        """Spawn and track a background coroutine."""
        task = asyncio.create_task(coro, name=name)
        self._active_tasks.add(task)

        def _cleanup(t: asyncio.Task[Any]) -> None:
            self._active_tasks.discard(t)
            if not t.cancelled():
                exc = t.exception()
                if exc:
                    logger.error(f"Background task {t.get_name()} raised exception: {exc}", exc_info=exc)

        task.add_done_callback(_cleanup)
        return task

    async def cancel_all(self, timeout_s: float = 2.0) -> None:
        """Gracefully cancel all running active tasks."""
        if not self._active_tasks:
            return
        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()

        try:
            await asyncio.wait_for(
                asyncio.gather(*list(self._active_tasks), return_exceptions=True),
                timeout=timeout_s,
            )
        except TimeoutError:
            logger.warning("Timeout waiting for background tasks to cancel")
        finally:
            self._active_tasks.clear()

    def get_dispatch_latency_p99_ms(self) -> float:
        """Compute p99 dispatch latency in milliseconds."""
        if not self._dispatch_latencies_ns:
            return 0.0
        sorted_latencies = sorted(self._dispatch_latencies_ns)
        idx = int(0.99 * (len(sorted_latencies) - 1))
        return sorted_latencies[idx] / 1_000_000.0

    @property
    def active_task_count(self) -> int:
        return len(self._active_tasks)


engine = AsyncEngine()
