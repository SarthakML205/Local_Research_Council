"""Telemetry, tracing, and resilient failure logging."""

from app.backend.telemetry.collector import TelemetryCollector, telemetry_collector
from app.backend.telemetry.events import (
    BaseTelemetryRecord,
    EmbeddingEvent,
    FailureAckRecord,
    FailureCode,
    FailureRecord,
    LLMCallRecord,
    RetrievalEvent,
    Severity,
    StateTransitionEvent,
    SystemSampleEvent,
)
from app.backend.telemetry.failure_log import (
    FailureLogger,
    failure_logger,
    setup_global_exception_handlers,
)
from app.backend.telemetry.store import TelemetryStore, telemetry_store
from app.backend.telemetry.tracer import (
    instrument_embeddings,
    instrument_llm,
    instrument_retrieval,
    parent_span_id_var,
    session_id_var,
    span,
    span_id_var,
    trace_id_var,
)

__all__ = [
    "TelemetryCollector",
    "telemetry_collector",
    "BaseTelemetryRecord",
    "LLMCallRecord",
    "RetrievalEvent",
    "EmbeddingEvent",
    "SystemSampleEvent",
    "StateTransitionEvent",
    "FailureRecord",
    "FailureAckRecord",
    "Severity",
    "FailureCode",
    "FailureLogger",
    "failure_logger",
    "setup_global_exception_handlers",
    "TelemetryStore",
    "telemetry_store",
    "span",
    "instrument_llm",
    "instrument_retrieval",
    "instrument_embeddings",
    "session_id_var",
    "trace_id_var",
    "span_id_var",
    "parent_span_id_var",
]
