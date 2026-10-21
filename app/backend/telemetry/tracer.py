"""Trace context propagation and execution decorators."""

import contextvars
import functools
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

# Trace context variables across asyncio coroutines
session_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("session_id", default="")
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
span_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")
parent_span_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("parent_span_id", default="")

F = TypeVar("F", bound=Callable[..., Any])


class SpanContext:
    """Async context manager that creates a child span and restores the previous context on exit."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.span_id = str(uuid.uuid4())[:8]
        self._prev_span_id: str | None = None
        self._prev_parent_span_id: str | None = None
        self.start_ns: int = 0
        self.duration_ns: int = 0

    async def __aenter__(self) -> "SpanContext":
        self.start_ns = time.perf_counter_ns()
        self._prev_parent_span_id = parent_span_id_var.get()
        self._prev_span_id = span_id_var.get()

        parent_span_id_var.set(self._prev_span_id or "")
        span_id_var.set(self.span_id)
        if not trace_id_var.get():
            trace_id_var.set(str(uuid.uuid4()))
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.duration_ns = time.perf_counter_ns() - self.start_ns
        if self._prev_span_id is not None:
            span_id_var.set(self._prev_span_id)
        if self._prev_parent_span_id is not None:
            parent_span_id_var.set(self._prev_parent_span_id)


def span(name: str) -> SpanContext:
    """Context manager for tracing execution blocks."""
    return SpanContext(name)


def instrument_llm(purpose: str) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorator to trace local LLM inference invocations."""

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async with span(f"llm:{purpose}"):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def instrument_retrieval(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to trace vector and hybrid retrieval queries."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with span("retrieval:query"):
            return await func(*args, **kwargs)

    return wrapper


def instrument_embeddings(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to trace MLX embedding batches."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        async with span("embeddings:batch"):
            return await func(*args, **kwargs)

    return wrapper
