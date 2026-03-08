"""Custom metrics collection for monitoring agent performance."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from hotel_agent.observability.tracing import get_langfuse, score_trace

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics captured for a single query."""
    trace_id: str
    session_id: str
    intent: str
    agent_used: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_calls: int = 0
    rag_chunks_retrieved: int = 0
    escalated: bool = False
    error: str | None = None


# In-memory metrics store (in production, use a time-series DB)
_metrics_store: list[QueryMetrics] = []


def record_query_metrics(metrics: QueryMetrics) -> None:
    """Record metrics for a completed query and push scores to Langfuse."""
    _metrics_store.append(metrics)

    # Push key metrics as Langfuse scores for dashboard filtering
    score_trace(metrics.trace_id, "latency_ms", metrics.latency_ms)
    if metrics.estimated_cost_usd > 0:
        score_trace(metrics.trace_id, "cost_usd", metrics.estimated_cost_usd)
    if metrics.escalated:
        score_trace(metrics.trace_id, "escalated", 1.0, "Query escalated to human")

    logger.info(
        "Recorded metrics: trace=%s intent=%s agent=%s latency=%.0fms tokens=%d",
        metrics.trace_id,
        metrics.intent,
        metrics.agent_used,
        metrics.latency_ms,
        metrics.total_tokens,
    )


def get_performance_summary() -> dict[str, Any]:
    """Aggregate performance summary across all recorded queries."""
    if not _metrics_store:
        return {"total_queries": 0, "message": "No queries recorded yet"}

    total = len(_metrics_store)
    by_intent: dict[str, list[QueryMetrics]] = defaultdict(list)
    by_agent: dict[str, list[QueryMetrics]] = defaultdict(list)

    for m in _metrics_store:
        by_intent[m.intent].append(m)
        by_agent[m.agent_used].append(m)

    def _agg(items: list[QueryMetrics]) -> dict:
        latencies = [m.latency_ms for m in items]
        costs = [m.estimated_cost_usd for m in items]
        tokens = [m.total_tokens for m in items]
        errors = sum(1 for m in items if m.error)
        escalated = sum(1 for m in items if m.escalated)
        return {
            "count": len(items),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 1),
            "total_cost_usd": round(sum(costs), 4),
            "avg_tokens": round(sum(tokens) / len(tokens)),
            "error_rate": round(errors / len(items), 3),
            "escalation_rate": round(escalated / len(items), 3),
        }

    return {
        "total_queries": total,
        "overall": _agg(_metrics_store),
        "by_intent": {k: _agg(v) for k, v in by_intent.items()},
        "by_agent": {k: _agg(v) for k, v in by_agent.items()},
    }


def estimate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o") -> float:
    """Estimate USD cost based on token counts. Prices as of early 2026."""
    pricing = {
        "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
        "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    }
    rates = pricing.get(model, pricing["gpt-4o"])
    return round(input_tokens * rates["input"] + output_tokens * rates["output"], 6)


class LatencyTimer:
    """Simple timer for measuring operation latency."""

    def __init__(self) -> None:
        self._start: float = 0

    def start(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> float:
        return round((time.perf_counter() - self._start) * 1000, 2)
