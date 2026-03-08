"""Langfuse tracing integration — every agent call is traced end-to-end."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from langfuse.types import TraceContext

from hotel_agent.config import settings

logger = logging.getLogger(__name__)

_langfuse: Langfuse | None = None


def get_langfuse() -> Langfuse:
    """Singleton Langfuse client."""
    global _langfuse
    if _langfuse is None:
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return _langfuse


class _TraceHandle:
    """Thin wrapper around a root LangfuseSpan exposing trace-level operations.

    In Langfuse v3 there is no separate Trace object — a root span IS the trace.
    This wrapper makes the v3 span behave like the v2 Trace so that call-sites
    in main.py and the workflow don't need to change.
    """

    def __init__(self, span: Any, trace_id: str) -> None:
        self._span = span
        self.id = trace_id  # expose trace_id as .id (same as v2 trace.id)

    def update(self, output: Any = None, **kwargs: Any) -> None:
        """Update trace-level output / metadata."""
        self._span.update_trace(output=output, **kwargs)

    def span(self, name: str, input: Any = None, metadata: dict | None = None) -> Any:
        """Create a child span on this trace."""
        return self._span.start_span(name=name, input=input, metadata=metadata or {})


def create_langfuse_handler(
    trace_id: str,
    session_id: str = "",
    user_id: str = "",
) -> LangfuseCallbackHandler:
    """Create a LangChain callback handler that sends spans to Langfuse.

    In Langfuse v3 the handler accepts a TraceContext instead of raw creds.
    """
    return LangfuseCallbackHandler(
        trace_context=TraceContext(trace_id=trace_id),
        update_trace=True,
    )


def create_trace(
    name: str,
    session_id: str = "",
    user_id: str = "",
    input_data: Any = None,
    metadata: dict | None = None,
) -> _TraceHandle:
    """Create a new Langfuse trace for a customer query."""
    lf = get_langfuse()

    trace_id = Langfuse.create_trace_id()
    trace_context = TraceContext(trace_id=trace_id)

    span = lf.start_span(
        trace_context=trace_context,
        name=name,
        input=input_data,
        metadata=metadata or {},
    )
    # Attach session / user / input at the trace level
    span.update_trace(
        session_id=session_id or None,
        user_id=user_id or None,
        input=input_data,
    )

    logger.info("Created trace %s for session=%s", trace_id, session_id)
    return _TraceHandle(span, trace_id)


def score_trace(trace_id: str, name: str, value: float, comment: str = "") -> None:
    """Attach a score to a trace (e.g. evaluation result)."""
    lf = get_langfuse()
    lf.create_score(
        trace_id=trace_id,
        name=name,
        value=value,
        comment=comment,
    )


@contextmanager
def traced_span(
    trace: _TraceHandle,
    name: str,
    input_data: Any = None,
    metadata: dict | None = None,
) -> Generator[dict, None, None]:
    """Context manager that creates a Langfuse child span and auto-closes it.

    Usage:
        with traced_span(trace, "router") as span_ctx:
            result = do_work()
            span_ctx["output"] = result
    """
    span = trace.span(name=name, input=input_data, metadata=metadata)
    ctx: dict[str, Any] = {"span": span, "output": None, "error": None}
    start = time.perf_counter()
    try:
        yield ctx
    except Exception as exc:
        ctx["error"] = str(exc)
        span.update(output={"error": str(exc)})
        span.end()
        raise
    else:
        span.update(output=ctx.get("output"))
        span.end()


def flush() -> None:
    """Flush pending events to Langfuse. Call before shutdown."""
    lf = get_langfuse()
    lf.flush()


def check_health() -> bool:
    """Return True if Langfuse is reachable."""
    try:
        lf = get_langfuse()
        lf.auth_check()
        return True
    except Exception:
        logger.warning("Langfuse health check failed", exc_info=True)
        return False


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
