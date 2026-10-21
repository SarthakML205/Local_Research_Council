"""LRC Sovereign FastAPI Application Entrypoint.

Binds local multi-agent debate FSM, zero-relational library storage,
hardware physics telemetry watchdog, and SSE event streaming.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.debate_routes import router as debate_router
from app.api.library_routes import router as library_router
from app.api.stream import broadcaster
from app.api.stream import router as stream_router
from app.api.telemetry_routes import router as telemetry_router
from app.core.profiler import HardwareProfiler

logger: Final = logging.getLogger(__name__)

profiler: Final[HardwareProfiler] = HardwareProfiler()


async def hardware_broadcaster_task() -> None:
    """Background coroutine broadcasting hardware physics telemetry once per second."""
    try:
        while True:
            snap = profiler.sample_now()
            rss_mb = snap.rss_bytes / (1024 * 1024)
            await broadcaster.publish(
                "hardware",
                {
                    "timestamp_ns": snap.timestamp_ns,
                    "rss_mb": round(rss_mb, 2),
                    "rss_gb": round(snap.rss_gb, 3),
                    "metal_mb": round(snap.metal_bytes / (1024 * 1024), 2),
                    "total_unified_gb": round(snap.total_unified_gb, 3),
                    "is_warning": snap.warning_triggered,
                    "is_ceiling": snap.ceiling_triggered,
                },
            )
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager controlling background telemetry watchdog."""
    logger.info("Initializing Local Research Council sovereign backend...")
    task = asyncio.create_task(hardware_broadcaster_task())
    yield
    logger.info("Shutting down LRC backend...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app: Final[FastAPI] = FastAPI(
    title="Local Research Council (LRC) Sovereign API",
    description="Zero-cloud, multi-agent research copilot and debate engine on Apple Silicon.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enforce zero-cloud CORS restriction: Only localhost and 127.0.0.1
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(stream_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(debate_router, prefix="/api")
app.include_router(telemetry_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """LRC sovereign operational healthcheck."""
    return {
        "status": "healthy",
        "mode": "100% Sovereign Local",
        "zero_cloud_egress": True,
        "unified_memory_target_gb": 12.0,
        "unified_memory_abort_gb": 18.0,
    }
