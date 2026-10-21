"""Telemetry file store: daily CSV and JSONL rotation via atomic file_store."""

import datetime
from pathlib import Path
from typing import Any

from app.backend.telemetry.events import (
    BaseTelemetryRecord,
    EmbeddingEvent,
    FailureRecord,
    LLMCallRecord,
    RetrievalEvent,
    SystemSampleEvent,
)
from app.config import settings
from app.core.file_store import file_store

# CSV Headers matching MASTER_ARCHITECTURE_SPECIFICATION.md
LLM_CALL_HEADERS = [
    "call_id",
    "timestamp_ns",
    "trace_id",
    "session_id",
    "purpose",
    "agent_role",
    "paper_ids",
    "model_tag",
    "backend",
    "sampling_temp",
    "prompt_tokens_system",
    "prompt_tokens_rag",
    "prompt_tokens_history",
    "prompt_tokens_total",
    "completion_tokens",
    "total_tokens",
    "chunks_considered",
    "chunks_packed",
    "chunks_dropped",
    "queue_wait_ms",
    "ttft_ms",
    "total_latency_ms",
    "tokens_per_sec",
    "schema_valid",
    "retry_count",
    "retry_reason",
    "status",
    "error_ref",
    "mem_before_gb",
    "mem_after_gb",
    "metal_active_gb",
    "payload_ref",
]

RETRIEVAL_HEADERS = [
    "event_id",
    "timestamp_ns",
    "trace_id",
    "session_id",
    "query_hash",
    "collection_name",
    "paper_id",
    "debate_id",
    "agent_id",
    "dense_ms",
    "sparse_bm25_ms",
    "rrf_ms",
    "cross_encoder_ms",
    "total_retrieval_ms",
    "dense_candidates",
    "sparse_candidates",
    "fused_candidates",
    "chunks_selected",
    "tokens_packed",
    "partition_violation_attempted",
]

EMBEDDING_HEADERS = [
    "event_id",
    "timestamp_ns",
    "trace_id",
    "session_id",
    "batch_size",
    "chunk_count",
    "duration_ms",
    "chunks_per_sec",
    "vector_dim",
    "mem_delta_mb",
    "status",
]

SYSTEM_HEADERS = [
    "event_id",
    "timestamp_ns",
    "rss_bytes",
    "rss_gb",
    "metal_active_bytes",
    "metal_active_gb",
    "total_unified_gb",
    "cpu_percent",
    "warning_triggered",
    "ceiling_triggered",
]


class TelemetryStore:
    """Manages append-only CSV and JSONL telemetry persistence with date-based rotation."""

    def __init__(self, base_dir: Path = settings.TELEMETRY_DIR) -> None:
        self.base_dir = base_dir

    def _get_date_str(self) -> str:
        return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

    async def write_llm_calls(self, records: list[LLMCallRecord]) -> None:
        if not records:
            return
        date_str = self._get_date_str()
        file_path = self.base_dir / "llm_calls" / f"{date_str}.csv"
        rows = [rec.model_dump() for rec in records]
        await file_store.append_csv_rows(file_path, LLM_CALL_HEADERS, rows)

    async def write_retrievals(self, records: list[RetrievalEvent]) -> None:
        if not records:
            return
        date_str = self._get_date_str()
        file_path = self.base_dir / "retrieval" / f"{date_str}.csv"
        rows = [rec.model_dump() for rec in records]
        await file_store.append_csv_rows(file_path, RETRIEVAL_HEADERS, rows)

    async def write_embeddings(self, records: list[EmbeddingEvent]) -> None:
        if not records:
            return
        date_str = self._get_date_str()
        file_path = self.base_dir / "embeddings" / f"{date_str}.csv"
        rows = [rec.model_dump() for rec in records]
        await file_store.append_csv_rows(file_path, EMBEDDING_HEADERS, rows)

    async def write_system_samples(self, records: list[SystemSampleEvent]) -> None:
        if not records:
            return
        date_str = self._get_date_str()
        file_path = self.base_dir / "system" / f"{date_str}.csv"
        rows = [rec.model_dump() for rec in records]
        await file_store.append_csv_rows(file_path, SYSTEM_HEADERS, rows)

    async def write_events(self, records: list[BaseTelemetryRecord]) -> None:
        if not records:
            return
        date_str = self._get_date_str()
        file_path = self.base_dir / "events" / f"{date_str}.jsonl"
        rows = [rec.model_dump() for rec in records]
        await file_store.append_jsonl(file_path, rows)

    async def write_failures(self, records: list[FailureRecord]) -> None:
        if not records:
            return
        date_str = self._get_date_str()
        file_path = self.base_dir / "failures" / f"{date_str}.jsonl"
        rows = [rec.model_dump() for rec in records]
        # Always sync failure records immediately
        await file_store.append_jsonl(file_path, rows, sync_immediately=True)

    async def read_failures(self, date_str: str | None = None) -> list[dict[str, Any]]:
        date = date_str or self._get_date_str()
        file_path = self.base_dir / "failures" / f"{date}.jsonl"
        records, _ = await file_store.read_jsonl_tolerant(file_path)
        return records

    async def read_llm_calls(self, date_str: str | None = None) -> list[dict[str, str]]:
        date = date_str or self._get_date_str()
        file_path = self.base_dir / "llm_calls" / f"{date}.csv"
        rows, _ = await file_store.read_csv_tolerant(file_path)
        return rows


telemetry_store = TelemetryStore()
