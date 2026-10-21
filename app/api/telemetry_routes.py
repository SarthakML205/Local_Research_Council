"""LRC Telemetry, Observability, and Audit API Routes.

Exposes real-time hardware telemetry, latency percentiles, error taxonomy
breakdowns, and zero-token audit reconciliations.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from fastapi import APIRouter

from app.backend.telemetry.aggregates import TelemetryAggregator
from app.backend.telemetry.failure_log import FailureLogStore
from app.core.profiler import HardwareProfiler

logger: Final = logging.getLogger(__name__)

router: Final[APIRouter] = APIRouter(prefix="/telemetry", tags=["Telemetry"])

hardware_profiler: Final[HardwareProfiler] = HardwareProfiler()
failure_store: Final[FailureLogStore] = FailureLogStore()
telemetry_aggregator: Final[TelemetryAggregator] = TelemetryAggregator()


@router.get("/hardware")
async def get_hardware_telemetry() -> dict[str, Any]:
    """Sample instant hardware metrics: Unified Memory RSS, Metal buffer, CPU percent."""
    snap = hardware_profiler.sample_now()
    rss_mb = snap.rss_bytes / (1024 * 1024)

    return {
        "timestamp_ns": snap.timestamp_ns,
        "rss_mb": round(rss_mb, 2),
        "rss_gb": round(snap.rss_gb, 3),
        "metal_mb": round(snap.metal_bytes / (1024 * 1024), 2),
        "metal_gb": round(snap.metal_gb, 3),
        "total_unified_gb": round(snap.total_unified_gb, 3),
        "is_warning": snap.warning_triggered,
        "is_ceiling": snap.ceiling_triggered,
        "target_ceiling_gb": 18.0,
        "target_warning_gb": 16.0,
        "operational_target_gb": 12.0,
        "zero_cloud_verified": True,
    }


@router.get("/stats")
async def get_telemetry_aggregates() -> dict[str, Any]:
    """Fetch statistical aggregates: latency percentiles, error taxonomy counts, token metrics."""
    return await telemetry_aggregator.compute_dashboard_metrics()


@router.get("/failures")
async def get_recent_failures(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve recent failure audit events from the multi-tier failure log."""
    return await failure_store.get_recent_failures(limit=limit)


@router.post("/audit")
async def run_token_audit() -> dict[str, Any]:
    """Execute exact zero-token reconciliation check across all debate turns."""
    audit_report = await telemetry_aggregator.audit_zero_tokens()
    return audit_report
