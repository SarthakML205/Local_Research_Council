"""Strict Pydantic contracts for telemetry events, metrics, and failures."""

import enum
import time
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Severity(enum.StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class FailureCode(enum.StrEnum):
    ARXIV_FETCH_ERROR = "ARXIV_FETCH_ERROR"
    PDF_PARSE_ERROR = "PDF_PARSE_ERROR"
    CHUNKING_ERROR = "CHUNKING_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_SCHEMA_VIOLATION = "LLM_SCHEMA_VIOLATION"
    LLM_BACKEND_ERROR = "LLM_BACKEND_ERROR"
    EMBED_ERROR = "EMBED_ERROR"
    QDRANT_ERROR = "QDRANT_ERROR"
    CITATION_UNGROUNDED = "CITATION_UNGROUNDED"
    DATA_FILE_CORRUPT = "DATA_FILE_CORRUPT"
    PARTITION_VIOLATION = "PARTITION_VIOLATION"
    TOKEN_BUDGET_BREACH = "TOKEN_BUDGET_BREACH"
    MEMORY_WARNING = "MEMORY_WARNING"
    MEMORY_CEILING = "MEMORY_CEILING"
    STATE_ROLLBACK = "STATE_ROLLBACK"
    NETWORK_GUARD_TRIGGER = "NETWORK_GUARD_TRIGGER"
    SSE_DISCONNECT = "SSE_DISCONNECT"
    LIBRARY_ERROR = "LIBRARY_ERROR"
    PAPER_STORAGE_ERROR = "PAPER_STORAGE_ERROR"
    COUNCIL_SELECTION_INVALID = "COUNCIL_SELECTION_INVALID"
    TELEMETRY_SINK_FALLBACK = "TELEMETRY_SINK_FALLBACK"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"


class BaseTelemetryRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_ns: int = Field(default_factory=time.perf_counter_ns)
    session_id: str = Field(default="")
    trace_id: str = Field(default="")
    span_id: str = Field(default="")
    parent_span_id: str = Field(default="")
    component: str = Field(default="core")
    state_revision_hash: str = Field(default="")


class FailureRecord(BaseTelemetryRecord):
    severity: Severity = Severity.ERROR
    code: FailureCode
    message: str
    exception_type: str = ""
    stack_trace: str = ""
    call_id: str = ""
    paper_id: str = ""
    debate_id: str = ""
    retry_attempt: int = 0
    resolution: Literal["retried", "rolled_back", "aborted", "degraded", "ignored", "pending"] = "pending"
    recovered: bool = False
    rss_gb: float = 0.0
    metal_gb: float = 0.0
    acknowledged: bool = False


class FailureAckRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    ack_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    failure_id: str
    timestamp_ns: int = Field(default_factory=time.perf_counter_ns)
    acknowledged_by: str = "user"


class LLMCallRecord(BaseTelemetryRecord):
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    purpose: Literal[
        "paper_extraction",
        "study_rerank",
        "mindmap_synthesis",
        "debate_turn",
        "moderator_review",
        "final_synthesis",
        "history_compression",
    ]
    agent_role: str = "system"
    paper_ids: str = ""  # Pipe-joined string for CSV compatibility
    model_tag: str
    backend: str = "ollama"
    sampling_temp: float = 0.0
    prompt_tokens_system: int = 0
    prompt_tokens_rag: int = 0
    prompt_tokens_history: int = 0
    prompt_tokens_total: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    chunks_considered: int = 0
    chunks_packed: int = 0
    chunks_dropped: int = 0
    queue_wait_ms: float = 0.0
    ttft_ms: float = 0.0
    total_latency_ms: float = 0.0
    tokens_per_sec: float = 0.0
    schema_valid: bool = True
    retry_count: int = 0
    retry_reason: str = ""
    status: Literal[
        "ok",
        "retried_ok",
        "timeout",
        "schema_error",
        "budget_breach",
        "cancelled",
        "error",
    ] = "ok"
    error_ref: str = ""
    mem_before_gb: float = 0.0
    mem_after_gb: float = 0.0
    metal_active_gb: float = 0.0
    payload_ref: str = ""


class RetrievalEvent(BaseTelemetryRecord):
    query_hash: str
    collection_name: str
    paper_id: str
    debate_id: str = ""
    agent_id: str = ""
    dense_ms: float = 0.0
    sparse_bm25_ms: float = 0.0
    rrf_ms: float = 0.0
    cross_encoder_ms: float = 0.0
    total_retrieval_ms: float = 0.0
    dense_candidates: int = 0
    sparse_candidates: int = 0
    fused_candidates: int = 0
    chunks_selected: int = 0
    tokens_packed: int = 0
    partition_violation_attempted: bool = False


class EmbeddingEvent(BaseTelemetryRecord):
    batch_size: int
    chunk_count: int
    duration_ms: float
    chunks_per_sec: float
    vector_dim: int = 1024
    mem_delta_mb: float = 0.0
    status: Literal["ok", "error"] = "ok"


class SystemSampleEvent(BaseTelemetryRecord):
    rss_bytes: int
    rss_gb: float
    metal_active_bytes: int = 0
    metal_active_gb: float = 0.0
    total_unified_gb: float
    cpu_percent: float = 0.0
    warning_triggered: bool = False
    ceiling_triggered: bool = False


class StateTransitionEvent(BaseTelemetryRecord):
    from_state: str
    to_state: str
    revision: int
    revision_hash: str
    trigger: str = ""
    duration_ns: int = 0
    is_rollback: bool = False
