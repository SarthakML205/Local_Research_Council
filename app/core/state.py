"""Immutable FSM state container with BLAKE2b monotonic revision hashes and deterministic rollback."""

import asyncio
import enum
import hashlib
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SystemState(enum.StrEnum):
    IDLE = "IDLE"
    SCRAPING = "SCRAPING"
    EXTRACTING = "EXTRACTING"
    INDEXING = "INDEXING"
    GRAPH_READY = "GRAPH_READY"
    DEBATING = "DEBATING"
    ERROR = "ERROR"


# Valid forward and recovery transitions
LEGAL_TRANSITIONS: dict[SystemState, set[SystemState]] = {
    SystemState.IDLE: {SystemState.SCRAPING, SystemState.DEBATING, SystemState.ERROR},
    SystemState.SCRAPING: {SystemState.EXTRACTING, SystemState.IDLE, SystemState.ERROR},
    SystemState.EXTRACTING: {SystemState.INDEXING, SystemState.IDLE, SystemState.ERROR},
    SystemState.INDEXING: {SystemState.GRAPH_READY, SystemState.IDLE, SystemState.ERROR},
    SystemState.GRAPH_READY: {SystemState.DEBATING, SystemState.SCRAPING, SystemState.IDLE, SystemState.ERROR},
    SystemState.DEBATING: {SystemState.GRAPH_READY, SystemState.IDLE, SystemState.ERROR},
    SystemState.ERROR: {SystemState.IDLE, SystemState.SCRAPING, SystemState.DEBATING},
}


class StateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    state: SystemState
    revision: int
    revision_hash: str
    timestamp_ns: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class StateManager:
    """Thread-safe, deterministic state machine with cryptographic revision hashes and rollback."""

    def __init__(self, initial_state: SystemState = SystemState.IDLE) -> None:
        self._lock = asyncio.Lock()
        init_ts = time.perf_counter_ns()
        init_hash = hashlib.blake2b(f"root:0:{initial_state.value}:{init_ts}".encode(), digest_size=8).hexdigest()
        self._current = StateSnapshot(
            state=initial_state,
            revision=0,
            revision_hash=init_hash,
            timestamp_ns=init_ts,
            metadata={},
        )
        self._history: list[StateSnapshot] = [self._current]
        self._subscribers: set[asyncio.Queue[StateSnapshot]] = set()

    @property
    def current(self) -> StateSnapshot:
        return self._current

    @property
    def history(self) -> list[StateSnapshot]:
        return list(self._history)

    async def transition_to(
        self,
        target_state: SystemState,
        metadata: dict[str, Any] | None = None,
        force: bool = False,
    ) -> StateSnapshot:
        """Perform atomic state transition, advance revision, compute BLAKE2b hash, and broadcast."""
        t_start = time.perf_counter_ns()
        async with self._lock:
            current_state = self._current.state
            if not force and target_state not in LEGAL_TRANSITIONS.get(current_state, set()):
                raise ValueError(
                    f"Illegal transition from {current_state.value} to {target_state.value}. "
                    f"Legal targets: {[s.value for s in LEGAL_TRANSITIONS.get(current_state, set())]}"
                )

            next_revision = self._current.revision + 1
            now_ns = time.perf_counter_ns()
            # Cryptographic monotonic hash chaining
            raw_hash_material = (
                f"{self._current.revision_hash}:{next_revision}:{current_state.value}:"
                f"{target_state.value}:{now_ns}"
            )
            next_hash = hashlib.blake2b(raw_hash_material.encode(), digest_size=8).hexdigest()

            new_snapshot = StateSnapshot(
                state=target_state,
                revision=next_revision,
                revision_hash=next_hash,
                timestamp_ns=now_ns,
                metadata={
                    **(metadata or {}),
                    "transition_dispatch_ns": time.perf_counter_ns() - t_start,
                },
            )

            self._current = new_snapshot
            self._history.append(new_snapshot)

            # Non-blocking broadcast to SSE subscribers
            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(new_snapshot)
                except asyncio.QueueFull:
                    # Subscriber fell behind, drop oldest
                    try:
                        queue.get_nowait()
                        queue.put_nowait(new_snapshot)
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        pass

            return new_snapshot

    async def rollback(self, target_revision: int | None = None) -> StateSnapshot:
        """Roll back state deterministically to a prior revision in < 5 ms."""
        t_start = time.perf_counter_ns()
        async with self._lock:
            if len(self._history) <= 1:
                return self._current

            target_snapshot: StateSnapshot | None = None
            if target_revision is None:
                # Rollback to the immediate previous snapshot
                target_snapshot = self._history[-2]
            else:
                for snap in reversed(self._history):
                    if snap.revision == target_revision:
                        target_snapshot = snap
                        break

            if target_snapshot is None:
                raise ValueError(f"Revision {target_revision} not found in history")

            now_ns = time.perf_counter_ns()
            next_rev = self._current.revision + 1
            raw_hash_material = (
                f"{self._current.revision_hash}:{next_rev}:ROLLBACK_TO_{target_snapshot.revision}:"
                f"{target_snapshot.state.value}:{now_ns}"
            )
            rollback_hash = hashlib.blake2b(raw_hash_material.encode(), digest_size=8).hexdigest()

            rollback_snapshot = StateSnapshot(
                state=target_snapshot.state,
                revision=next_rev,
                revision_hash=rollback_hash,
                timestamp_ns=now_ns,
                metadata={
                    "rollback_source_revision": self._current.revision,
                    "rollback_target_revision": target_snapshot.revision,
                    "rollback_latency_ns": time.perf_counter_ns() - t_start,
                },
            )

            self._current = rollback_snapshot
            self._history.append(rollback_snapshot)

            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(rollback_snapshot)
                except asyncio.QueueFull:
                    pass

            return rollback_snapshot

    def subscribe(self, max_buffer: int = 100) -> asyncio.Queue[StateSnapshot]:
        """Create a state subscription queue for SSE streaming."""
        queue: asyncio.Queue[StateSnapshot] = asyncio.Queue(maxsize=max_buffer)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[StateSnapshot]) -> None:
        """Remove a state subscription."""
        self._subscribers.discard(queue)


state_manager = StateManager()
