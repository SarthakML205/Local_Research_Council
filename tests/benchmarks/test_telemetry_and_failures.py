"""Benchmark and Verification Suite for Telemetry, Zero-Token Reconciliation, and Fault Injection.

Tests:
1. Exact zero-token reconciliation (recorded tokens match inference metrics with zero drift).
2. Fault injection captures typed failures into multi-tier sink chain (disk CSV/JSONL + memory).
3. Telemetry statistical aggregation accurately computes p50, p95, p99 latencies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.backend.telemetry.aggregates import TelemetryAggregator
from app.backend.telemetry.events import (
    FailureCode,
    Severity,
)
from app.backend.telemetry.failure_log import FailureLogStore


@pytest.mark.asyncio
async def test_exact_zero_token_reconciliation() -> None:
    """Assertion: Zero-token audit verifies reported LLM tokens match recorded ledger."""
    aggregator = TelemetryAggregator()

    # Emit 5 recorded turns
    tokens_recorded = [120, 350, 410, 890, 200]
    for i, tok in enumerate(tokens_recorded):
        aggregator.record_turn_tokens(
            debate_id="deb_audit_test",
            turn_index=i + 1,
            tokens=tok,
        )

    audit_result = await aggregator.audit_zero_tokens()
    assert audit_result["total_tokens_recorded"] == sum(tokens_recorded)
    assert audit_result["reconciliation_discrepancy"] == 0
    assert audit_result["status"] == "verified_zero_leakage"


@pytest.mark.asyncio
async def test_fault_injection_logging(tmp_path: Path) -> None:
    """Assertion: Fault injection routes typed failure records into multi-tier sink chain."""
    failure_store = FailureLogStore(log_dir=tmp_path / "telemetry_logs")

    # Injected faults
    faults = [
        (FailureCode.CITATION_UNGROUNDED, "Hallucinated chunk [P1 §9 #99] not present in context"),
        (FailureCode.NETWORK_GUARD_TRIGGER, "Forbidden WAN egress attempt detected to 8.8.8.8"),
        (FailureCode.PARTITION_VIOLATION, "Advocate p1 attempted cross-paper access to p2"),
        (FailureCode.TOKEN_BUDGET_BREACH, "Prompt exceeded 2,048 tokens before knapsack trimming"),
    ]

    for code, message in faults:
        await failure_store.log_failure(
            code=code,
            message=message,
            severity=Severity.ERROR,
            component="test_suite",
        )

    # Retrieve recent failures
    recent = await failure_store.get_recent_failures(limit=10)
    assert len(recent) >= 4

    logged_codes = {r["code"] for r in recent}
    for code, _ in faults:
        assert code.value in logged_codes, f"Fault {code.value} not recorded in failure sink"


@pytest.mark.asyncio
async def test_telemetry_aggregation_and_percentiles() -> None:
    """Assertion: Statistical aggregator calculates accurate p50, p95, p99 latencies."""
    aggregator = TelemetryAggregator()

    # Feed 100 sample latencies (1 ms to 100 ms)
    for ms in range(1, 101):
        aggregator.record_latency("inference", float(ms))

    metrics = await aggregator.compute_dashboard_metrics()
    assert "latencies" in metrics
    lat = metrics["latencies"]

    # p50 ~ 50ms, p95 ~ 95ms, p99 ~ 99ms
    assert 48.0 <= lat["p50_ms"] <= 52.0, f"p50 calculation drift: {lat['p50_ms']}"
    assert 93.0 <= lat["p95_ms"] <= 97.0, f"p95 calculation drift: {lat['p95_ms']}"
    assert 97.0 <= lat["p99_ms"] <= 100.0, f"p99 calculation drift: {lat['p99_ms']}"
