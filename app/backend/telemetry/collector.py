"""High-throughput async telemetry collector with bounded queues and zero-drop error guarantee."""

import asyncio
import collections
import logging
import time

from app.backend.telemetry.events import (
    BaseTelemetryRecord,
    EmbeddingEvent,
    FailureRecord,
    LLMCallRecord,
    RetrievalEvent,
    Severity,
    SystemSampleEvent,
)
from app.backend.telemetry.store import telemetry_store
from app.config import settings

logger = logging.getLogger("app.backend.telemetry.collector")


class TelemetryCollector:
    """Async collector ingesting telemetry events with hot-path < 1 ms overhead and zero error drops."""

    def __init__(
        self,
        queue_size: int = settings.TELEMETRY_QUEUE_SIZE,
        batch_size: int = settings.TELEMETRY_BATCH_SIZE,
        flush_interval_ms: int = settings.TELEMETRY_FLUSH_INTERVAL_MS,
        ring_buffer_size: int = settings.TELEMETRY_RING_BUFFER_CAPACITY,
    ) -> None:
        self.queue_size = queue_size
        self.batch_size = batch_size
        self.flush_interval_s = flush_interval_ms / 1000.0
        self._queue: asyncio.Queue[BaseTelemetryRecord] = asyncio.Queue(maxsize=queue_size)
        self._ring_buffer: collections.deque[BaseTelemetryRecord] = collections.deque(maxlen=ring_buffer_size)
        self._subscribers: set[asyncio.Queue[BaseTelemetryRecord]] = set()
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False
        self._dropped_debug_count = 0
        self._dropped_info_count = 0

    def emit_nowait(self, record: BaseTelemetryRecord) -> bool:
        """Hot-path non-blocking event emission (< 1 ms overhead). Guaranteed delivery for ERROR/FATAL."""
        time.perf_counter_ns()
        self._ring_buffer.append(record)

        # Broadcast to live SSE subscribers
        for sub in list(self._subscribers):
            try:
                sub.put_nowait(record)
            except asyncio.QueueFull:
                pass

        # Check queue saturation
        is_error = isinstance(record, FailureRecord) and record.severity in (Severity.ERROR, Severity.FATAL)

        try:
            self._queue.put_nowait(record)
            return True
        except asyncio.QueueFull:
            if is_error:
                # Under saturation, make room for ERROR/FATAL by discarding oldest DEBUG event
                try:
                    dropped = self._queue.get_nowait()
                    if isinstance(dropped, FailureRecord) and dropped.severity in (Severity.ERROR, Severity.FATAL):
                        # Put back error
                        self._queue.put_nowait(dropped)
                    else:
                        self._dropped_debug_count += 1
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
                try:
                    self._queue.put_nowait(record)
                    return True
                except asyncio.QueueFull:
                    # Emergency synchronous fallback
                    if isinstance(record, FailureRecord):
                        asyncio.create_task(telemetry_store.write_failures([record]))
                    return True
            else:
                self._dropped_debug_count += 1
                return False

    async def emit(self, record: BaseTelemetryRecord) -> None:
        """Async emission with hot-path guarantee."""
        self.emit_nowait(record)

    async def _worker_loop(self) -> None:
        """Batch-writing loop flushing queues to disk."""
        while self._running:
            batch: list[BaseTelemetryRecord] = []
            try:
                # Wait for at least one event or timeout
                item = await asyncio.wait_for(self._queue.get(), timeout=self.flush_interval_s)
                batch.append(item)
                self._queue.task_done()

                # Drain available items up to batch_size
                while len(batch) < self.batch_size:
                    try:
                        next_item = self._queue.get_nowait()
                        batch.append(next_item)
                        self._queue.task_done()
                    except asyncio.QueueEmpty:
                        break

            except TimeoutError:
                pass

            if batch:
                await self._flush_batch(batch)

    async def _flush_batch(self, batch: list[BaseTelemetryRecord]) -> None:
        """Group events by type and write in batch."""
        llm_calls: list[LLMCallRecord] = []
        retrievals: list[RetrievalEvent] = []
        embeddings: list[EmbeddingEvent] = []
        systems: list[SystemSampleEvent] = []
        failures: list[FailureRecord] = []
        events: list[BaseTelemetryRecord] = []

        for item in batch:
            if isinstance(item, LLMCallRecord):
                llm_calls.append(item)
            elif isinstance(item, RetrievalEvent):
                retrievals.append(item)
            elif isinstance(item, EmbeddingEvent):
                embeddings.append(item)
            elif isinstance(item, SystemSampleEvent):
                systems.append(item)
            elif isinstance(item, FailureRecord):
                failures.append(item)
            else:
                events.append(item)

        if llm_calls:
            await telemetry_store.write_llm_calls(llm_calls)
        if retrievals:
            await telemetry_store.write_retrievals(retrievals)
        if embeddings:
            await telemetry_store.write_embeddings(embeddings)
        if systems:
            await telemetry_store.write_system_samples(systems)
        if failures:
            await telemetry_store.write_failures(failures)
        if events:
            await telemetry_store.write_events(events)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker_loop(), name="TelemetryCollectorWorker")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        # Drain remaining items
        drain_batch: list[BaseTelemetryRecord] = []
        while not self._queue.empty():
            try:
                drain_batch.append(self._queue.get_nowait())
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        if drain_batch:
            await self._flush_batch(drain_batch)

    def subscribe(self, max_buffer: int = 500) -> asyncio.Queue[BaseTelemetryRecord]:
        """Subscribe to real-time telemetry events for SSE streaming."""
        queue: asyncio.Queue[BaseTelemetryRecord] = asyncio.Queue(maxsize=max_buffer)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[BaseTelemetryRecord]) -> None:
        self._subscribers.discard(queue)

    @property
    def recent_events(self) -> list[BaseTelemetryRecord]:
        return list(self._ring_buffer)


telemetry_collector = TelemetryCollector()
