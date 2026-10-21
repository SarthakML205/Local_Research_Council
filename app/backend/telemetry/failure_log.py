"""Resilient failure logger with fallback sink chain and global exception traps."""

import asyncio
import logging
import sys
import traceback
from pathlib import Path
from typing import Any

from app.backend.telemetry.events import FailureCode, FailureRecord, Severity
from app.backend.telemetry.store import telemetry_store
from app.backend.telemetry.tracer import session_id_var, span_id_var, trace_id_var
from app.config import settings

logger = logging.getLogger("app.backend.telemetry.failure_log")


class FailureLogger:
    """Never-silent failure capture system with 3-tier fallback sink chain."""

    def __init__(
        self,
        fallback_log_path: Path = settings.LOGS_DIR / "fallback.jsonl",
    ) -> None:
        self.fallback_log_path = fallback_log_path
        self._fallback_active = False

    def emit_to_stderr(self, record: FailureRecord) -> None:
        """Tier 3 sink: direct stderr flush."""
        try:
            sys.stderr.write(f"[CRITICAL_FALLBACK_FAILURE] {record.model_dump_json()}\n")
            sys.stderr.flush()
        except Exception:
            pass

    def emit_to_fallback_file(self, record: FailureRecord) -> bool:
        """Tier 2 sink: append-only fallback JSONL file."""
        try:
            self.fallback_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.fallback_log_path, "a", encoding="utf-8") as f:
                f.write(record.model_dump_json() + "\n")
                f.flush()
            return True
        except Exception as exc:
            logger.error(f"Fallback file sink failed: {exc}")
            self.emit_to_stderr(record)
            return False

    async def log_failure(
        self,
        code: FailureCode,
        message: str,
        severity: Severity = Severity.ERROR,
        exception: BaseException | None = None,
        component: str = "core",
        call_id: str = "",
        paper_id: str = "",
        debate_id: str = "",
        retry_attempt: int = 0,
        state_revision_hash: str = "",
    ) -> FailureRecord:
        """Emit a structured FailureRecord through the tiered sink chain."""
        exc_type = type(exception).__name__ if exception else ""
        stack_str = "".join(traceback.format_exception(exception)) if exception else ""

        record = FailureRecord(
            code=code,
            severity=severity,
            message=message,
            exception_type=exc_type,
            stack_trace=stack_str,
            component=component,
            trace_id=trace_id_var.get() or "",
            span_id=span_id_var.get() or "",
            session_id=session_id_var.get() or "",
            call_id=call_id,
            paper_id=paper_id,
            debate_id=debate_id,
            retry_attempt=retry_attempt,
            state_revision_hash=state_revision_hash,
        )

        # Primary sink: TelemetryStore
        try:
            await telemetry_store.write_failures([record])
            return record
        except Exception as primary_exc:
            # Fall back to Tier 2
            self._fallback_active = True
            fallback_notification = FailureRecord(
                code=FailureCode.TELEMETRY_SINK_FALLBACK,
                severity=Severity.FATAL,
                message=f"Primary telemetry failure store failed: {primary_exc}. Fallback active.",
                component="telemetry",
            )
            self.emit_to_fallback_file(fallback_notification)
            self.emit_to_fallback_file(record)
            return record

    def log_failure_sync(
        self,
        code: FailureCode,
        message: str,
        severity: Severity = Severity.ERROR,
        exception: BaseException | None = None,
        component: str = "core",
    ) -> FailureRecord:
        """Synchronous failure emission for excepthook and non-async contexts."""
        exc_type = type(exception).__name__ if exception else ""
        stack_str = "".join(traceback.format_exception(exception)) if exception else ""

        record = FailureRecord(
            code=code,
            severity=severity,
            message=message,
            exception_type=exc_type,
            stack_trace=stack_str,
            component=component,
        )
        if not self.emit_to_fallback_file(record):
            self.emit_to_stderr(record)
        return record


failure_logger = FailureLogger()


class FailureLogStore:
    """Convenience accessor for querying and logging typed failure records."""

    def __init__(self, log_dir: Path | None = None) -> None:
        self.logger = FailureLogger(fallback_log_path=(log_dir or settings.LOGS_DIR) / "fallback.jsonl")

    async def log_failure(
        self,
        code: FailureCode,
        message: str,
        severity: Severity = Severity.ERROR,
        component: str = "core",
        **kwargs: Any,
    ) -> FailureRecord:
        return await self.logger.log_failure(
            code=code,
            message=message,
            severity=severity,
            component=component,
            **kwargs,
        )

    async def get_recent_failures(self, limit: int = 50) -> list[dict[str, Any]]:
        records = await telemetry_store.read_failures()
        return records[-limit:]


failure_store = FailureLogStore()


def setup_global_exception_handlers(loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Install global exception hooks for sys and asyncio event loop."""

    def _sys_excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: Any,
    ) -> None:
        failure_logger.log_failure_sync(
            code=FailureCode.UNHANDLED_EXCEPTION,
            message=str(exc_value),
            severity=Severity.FATAL,
            exception=exc_value,
            component="runtime",
        )

    sys.excepthook = _sys_excepthook

    target_loop = loop or asyncio.get_event_loop()

    def _loop_exception_handler(
        loop: asyncio.AbstractEventLoop,
        context: dict[str, Any],
    ) -> None:
        exc = context.get("exception")
        msg = context.get("message", "Unhandled asyncio loop exception")
        failure_logger.log_failure_sync(
            code=FailureCode.UNHANDLED_EXCEPTION,
            message=str(msg),
            severity=Severity.FATAL,
            exception=exc if isinstance(exc, BaseException) else None,
            component="asyncio",
        )

    target_loop.set_exception_handler(_loop_exception_handler)
