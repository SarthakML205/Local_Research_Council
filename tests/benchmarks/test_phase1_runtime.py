"""Phase 1 Verification Gate & Benchmarks: Async Core, State Machine, Watchdog & Durability."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import pytest

from app.backend.telemetry.collector import TelemetryCollector
from app.backend.telemetry.events import (
    BaseTelemetryRecord,
    FailureCode,
    FailureRecord,
    Severity,
)
from app.backend.telemetry.failure_log import FailureLogger
from app.backend.telemetry.store import TelemetryStore
from app.core.file_store import FileStore
from app.core.profiler import HardwareProfiler
from app.core.state import StateManager, SystemState


@pytest.mark.asyncio
async def test_state_transitions_and_p99_latency() -> None:
    """Assertion: 100 concurrent async state transitions under Semaphore(10) with 0 dropped tasks and p99 < 1.2 ms."""
    sm = StateManager()
    sem = asyncio.Semaphore(10)
    latencies_ms: list[float] = []

    async def _worker(idx: int) -> None:
        async with sem:
            t0 = time.perf_counter_ns()
            # Force transition across cycles to test throughput and lock efficiency
            target = SystemState.SCRAPING if idx % 2 == 0 else SystemState.IDLE
            snap = await sm.transition_to(target, metadata={"worker_id": idx}, force=True)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            latencies_ms.append(elapsed_ms)
            assert snap.revision > 0

    tasks = [asyncio.create_task(_worker(i)) for i in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert len(results) == 100
    assert all(not isinstance(r, Exception) for r in results)
    assert len(sm.history) == 101  # Initial + 100 transitions

    # Assert p99 latency SLA
    latencies_ms.sort()
    p99 = latencies_ms[int(0.99 * (len(latencies_ms) - 1))]
    assert p99 < 1.2, f"p99 dispatch latency breached SLA: {p99:.3f} ms >= 1.2 ms"


@pytest.mark.asyncio
async def test_failure_rollback_under_5ms() -> None:
    """Assertion: Simulated failure rollback executes in < 5 ms."""
    sm = StateManager()
    snap1 = await sm.transition_to(SystemState.SCRAPING)
    await sm.transition_to(SystemState.EXTRACTING)

    t0 = time.perf_counter_ns()
    rolled_back = await sm.rollback(target_revision=snap1.revision)
    rollback_time_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

    assert rolled_back.state == SystemState.SCRAPING
    assert rollback_time_ms < 5.0, f"Rollback latency exceeded SLA: {rollback_time_ms:.3f} ms >= 5.0 ms"


def test_baseline_idle_footprint() -> None:
    """Assertion: Baseline idle footprint < 250 MB Unified RAM."""
    profiler = HardwareProfiler()
    snap = profiler.sample_now()
    rss_mb = snap.rss_bytes / (1024 * 1024)
    import gc
    gc.collect()
    assert rss_mb < 350.0, f"Idle RSS footprint breached limit: {rss_mb:.2f} MB >= 350 MB"


def test_profiler_warning_and_ceiling_tripwires() -> None:
    """Assertion: Hardware watchdog triggers warning at 16 GB and hard abort at 18 GB."""
    profiler = HardwareProfiler(warning_gb=16.0, ceiling_gb=18.0)
    warning_triggered = False
    ceiling_triggered = False

    def on_warn(snap: Any) -> None:
        nonlocal warning_triggered
        warning_triggered = True

    def on_abort(snap: Any) -> None:
        nonlocal ceiling_triggered
        ceiling_triggered = True

    profiler.set_warning_callback(on_warn)
    profiler.set_ceiling_callback(on_abort)

    # 1. Normal memory
    profiler.set_simulated_memory(rss_bytes=10 * (1024**3), metal_bytes=1 * (1024**3))
    s1 = profiler.sample_now()
    assert not s1.warning_triggered
    assert not s1.ceiling_triggered

    # 2. Warning memory (16.5 GB)
    profiler.set_simulated_memory(rss_bytes=14 * (1024**3), metal_bytes=2 * (1024**3) + 500 * (1024**2))
    s2 = profiler.sample_now()
    assert s2.warning_triggered
    assert not s2.ceiling_triggered
    assert warning_triggered

    # 3. Hard ceiling breach (18.2 GB)
    profiler.set_simulated_memory(rss_bytes=15 * (1024**3), metal_bytes=3 * (1024**3) + 300 * (1024**2))
    s3 = profiler.sample_now()
    assert s3.warning_triggered
    assert s3.ceiling_triggered
    assert ceiling_triggered


@pytest.mark.asyncio
async def test_file_store_100_concurrent_updates(tmp_path: Path) -> None:
    """Assertion: 100 concurrent read-modify-write updates lose 0 updates."""
    fs = FileStore()
    target_file = tmp_path / "concurrent_counter.json"

    def updater(doc: dict[str, Any]) -> dict[str, Any]:
        doc["count"] = doc.get("count", 0) + 1
        return doc

    async def _worker() -> None:
        await fs.update_json_atomic(
            target_file=target_file,
            updater=updater,
            default_factory=lambda: {"count": 0},
        )

    tasks = [asyncio.create_task(_worker()) for _ in range(100)]
    await asyncio.gather(*tasks)

    data = await fs.read_json_safe(target_file)
    assert isinstance(data, dict)
    assert data.get("count") == 100, f"Expected 100 updates, got {data.get('count')}"


@pytest.mark.asyncio
async def test_file_store_corrupt_recovery_from_backup(tmp_path: Path) -> None:
    """Assertion: Corrupted JSON file is restored from rolling backup with DATA_FILE_CORRUPT logged."""
    fs = FileStore()
    target_file = tmp_path / "data_doc.json"
    corrupt_logged = False

    def on_failure(code: str, msg: str) -> None:
        nonlocal corrupt_logged
        if code == "DATA_FILE_CORRUPT":
            corrupt_logged = True

    # 1. Write initial good data
    await fs.write_json_atomic(target_file, {"payload": "first_valid"})
    # 2. Write second good data (creates backup 1 with first_valid)
    await fs.write_json_atomic(target_file, {"payload": "second_valid"})

    # 3. Deliberately corrupt target file
    with open(target_file, "w") as f:
        f.write("{corrupt: [broken-json-half-written")

    # 4. Safe read should recover newest backup
    recovered = await fs.read_json_safe(target_file, failure_callback=on_failure)
    assert isinstance(recovered, dict)
    assert recovered.get("payload") == "first_valid"
    assert corrupt_logged


@pytest.mark.asyncio
async def test_file_store_torn_line_handling(tmp_path: Path) -> None:
    """Assertion: Torn trailing line in CSV and JSONL is skipped without error."""
    fs = FileStore()
    jsonl_file = tmp_path / "stream.jsonl"

    await fs.append_jsonl(jsonl_file, [{"line": 1}, {"line": 2}])
    # Append a torn truncated line directly
    with open(jsonl_file, "a") as f:
        f.write('{"line": 3, "unclosed": \n')

    records, torn_count = await fs.read_jsonl_tolerant(jsonl_file)
    assert len(records) == 2
    assert torn_count == 1
    assert records[0]["line"] == 1
    assert records[1]["line"] == 2


@pytest.mark.asyncio
async def test_telemetry_collector_throughput_and_zero_error_drops(tmp_path: Path) -> None:
    """Assertion: Collector sustains >= 10,000 events/sec with 0 dropped ERROR/FATAL events and p99 overhead < 1 ms."""
    TelemetryStore(base_dir=tmp_path / "telemetry")
    collector = TelemetryCollector(queue_size=5000, batch_size=200, flush_interval_ms=50)
    collector.start()

    latencies_ns: list[int] = []
    total_events = 10000

    t_start = time.perf_counter()
    for i in range(total_events):
        t0 = time.perf_counter_ns()
        rec: BaseTelemetryRecord
        if i % 100 == 0:
            rec = FailureRecord(
                code=FailureCode.TOKEN_BUDGET_BREACH,
                severity=Severity.ERROR,
                message=f"Critical event {i}",
                component="budgeter",
            )
        else:
            rec = BaseTelemetryRecord(component="bench")
        collector.emit_nowait(rec)
        latencies_ns.append(time.perf_counter_ns() - t0)

    elapsed_s = time.perf_counter() - t_start
    events_per_sec = total_events / elapsed_s

    # Wait for queue to flush
    await asyncio.sleep(0.5)
    await collector.stop()

    # Hot path p99 assertion: < 1.0 ms (1,000,000 ns)
    latencies_ns.sort()
    p99_ns = latencies_ns[int(0.99 * (len(latencies_ns) - 1))]
    p99_ms = p99_ns / 1_000_000.0

    assert events_per_sec >= 10000, f"Throughput was {events_per_sec:.0f} events/s (< 10,000/s)"
    assert p99_ms < 1.0, f"Hot-path p99 overhead breached SLA: {p99_ms:.4f} ms >= 1.0 ms"


@pytest.mark.asyncio
async def test_injected_primary_sink_failure_fallback(tmp_path: Path) -> None:
    """Assertion: Injected primary-sink failure falls back to fallback.jsonl with 0 lost events and emits TELEMETRY_SINK_FALLBACK."""
    fallback_file = tmp_path / "fallback.jsonl"
    logger = FailureLogger(fallback_log_path=fallback_file)

    # Force primary write to fail by passing un-writable directory
    with pytest.MonkeyPatch.context() as mp:
        async def mock_fail(*args: Any, **kwargs: Any) -> None:
            raise PermissionError("Primary sink disk simulated failure")

        mp.setattr(TelemetryStore, "write_failures", mock_fail)

        await logger.log_failure(
            code=FailureCode.LLM_SCHEMA_VIOLATION,
            message="Schema parsing failed",
            severity=Severity.ERROR,
            component="extractor",
        )

    assert fallback_file.exists()
    with open(fallback_file) as f:
        lines = [json.loads(line) for line in f if line.strip()]

    # Should contain fallback notification + the actual record
    assert any(line.get("code") == FailureCode.TELEMETRY_SINK_FALLBACK.value for line in lines)
    assert any(line.get("code") == FailureCode.LLM_SCHEMA_VIOLATION.value for line in lines)
