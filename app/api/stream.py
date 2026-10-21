"""LRC Server-Sent Events (SSE) Streaming Hub.

Provides zero-overhead, real-time reactive event streaming from local
hardware telemetry, state transitions, debate agent turns, and token meters.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Final

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

logger: Final = logging.getLogger(__name__)

router: Final[APIRouter] = APIRouter(prefix="/stream", tags=["Streaming"])


class EventBroadcaster:
    """In-memory event hub dispatching events to active SSE connections."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a new client queue."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=500)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Deregister client queue upon disconnect."""
        async with self._lock:
            self._subscribers.discard(q)

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Fan out an event payload to all active client queues."""
        msg: dict[str, Any] = {"type": event_type, "data": data}
        async with self._lock:
            subscribers = list(self._subscribers)

        for q in subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                try:
                    # Drop oldest message if client is lagging
                    q.get_nowait()
                    q.put_nowait(msg)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass


# Singleton broadcaster
broadcaster: Final[EventBroadcaster] = EventBroadcaster()


async def sse_event_generator(
    client_queue: asyncio.Queue[dict[str, Any]],
    request: Request,
) -> AsyncGenerator[str, None]:
    """Yield formatted SSE text blocks to the client socket."""
    try:
        while True:
            if await request.is_disconnected():
                break

            try:
                msg = await asyncio.wait_for(client_queue.get(), timeout=15.0)
                event_type = msg.get("type", "message")
                payload = json.dumps(msg.get("data", {}))
                yield f"event: {event_type}\ndata: {payload}\n\n"
            except TimeoutError:
                # SSE heartbeat ping to keep local TCP socket alive
                yield ": ping\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        await broadcaster.unsubscribe(client_queue)


@router.get("/events")
async def stream_events(request: Request) -> StreamingResponse:
    """Global SSE stream for hardware telemetry, state changes, and debate turns."""
    queue = await broadcaster.subscribe()
    return StreamingResponse(
        sse_event_generator(queue, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
