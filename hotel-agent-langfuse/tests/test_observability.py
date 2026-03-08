"""Tests for the observability layer — tracing, metrics, evaluation."""

import pytest
from unittest.mock import patch, MagicMock

from hotel_agent.observability.metrics import (
    LatencyTimer,
    QueryMetrics,
    estimate_cost,
    get_performance_summary,
    record_query_metrics,
    _metrics_store,
)


class TestLatencyTimer:
    def test_timer_measures_elapsed(self):
        import time
        timer = LatencyTimer()
        timer.start()
        time.sleep(0.01)  # 10ms
        elapsed = timer.elapsed_ms()
        assert elapsed >= 5  # At least ~5ms (accounting for OS variance)
        assert elapsed < 1000  # Less than 1 second


class TestCostEstimation:
    def test_gpt4o_cost(self):
        cost = estimate_cost(input_tokens=1000, output_tokens=500, model="gpt-4o")
        assert cost > 0
        # GPT-4o: 1000 * 2.5/1M + 500 * 10/1M = 0.0025 + 0.005 = 0.0075
        assert abs(cost - 0.0075) < 0.001

    def test_gpt4o_mini_cost(self):
        cost = estimate_cost(input_tokens=1000, output_tokens=500, model="gpt-4o-mini")
        assert cost > 0
        assert cost < estimate_cost(1000, 500, "gpt-4o")  # Mini should be cheaper

    def test_unknown_model_uses_gpt4o_rates(self):
        cost_unknown = estimate_cost(1000, 500, "unknown-model")
        cost_gpt4o = estimate_cost(1000, 500, "gpt-4o")
        assert cost_unknown == cost_gpt4o


class TestMetricsRecording:
    def setup_method(self):
        """Clear metrics store before each test."""
        _metrics_store.clear()

    @patch("hotel_agent.observability.metrics.score_trace")
    def test_record_query_metrics(self, mock_score):
        metrics = QueryMetrics(
            trace_id="test-trace-1",
            session_id="test-session",
            intent="booking",
            agent_used="booking_agent",
            latency_ms=250.0,
            total_tokens=500,
            estimated_cost_usd=0.005,
        )
        record_query_metrics(metrics)

        assert len(_metrics_store) == 1
        assert _metrics_store[0].trace_id == "test-trace-1"
        assert mock_score.called

    @patch("hotel_agent.observability.metrics.score_trace")
    def test_performance_summary_empty(self, mock_score):
        summary = get_performance_summary()
        assert summary["total_queries"] == 0

    @patch("hotel_agent.observability.metrics.score_trace")
    def test_performance_summary_with_data(self, mock_score):
        for i, intent in enumerate(["booking", "booking", "billing", "complaint"]):
            record_query_metrics(QueryMetrics(
                trace_id=f"trace-{i}",
                session_id=f"session-{i}",
                intent=intent,
                agent_used=f"{intent}_agent",
                latency_ms=100 + i * 50,
                total_tokens=300 + i * 100,
                escalated=(intent == "complaint"),
            ))

        summary = get_performance_summary()
        assert summary["total_queries"] == 4
        assert "booking" in summary["by_intent"]
        assert "billing" in summary["by_intent"]
        assert summary["by_intent"]["complaint"]["escalation_rate"] == 1.0
        assert summary["by_intent"]["booking"]["escalation_rate"] == 0.0


class TestToolMetrics:
    def test_booking_tools(self):
        """Test that booking tools return expected output."""
        from hotel_agent.tools.booking_tools import check_availability, create_booking

        result = check_availability.invoke({
            "room_type": "deluxe",
            "check_in": "2026-04-01",
            "check_out": "2026-04-03",
        })
        assert "Deluxe Room" in result
        assert "$219" in result

    def test_booking_invalid_type(self):
        from hotel_agent.tools.booking_tools import check_availability

        result = check_availability.invoke({
            "room_type": "nonexistent",
            "check_in": "2026-04-01",
            "check_out": "2026-04-03",
        })
        assert "Unknown room type" in result

    def test_billing_tools(self):
        from hotel_agent.tools.billing_tools import get_bill

        result = get_bill.invoke({"booking_id": "BK-1001"})
        assert "Alice Johnson" in result
        assert "BK-1001" in result

    def test_billing_missing(self):
        from hotel_agent.tools.billing_tools import get_bill

        result = get_bill.invoke({"booking_id": "BK-9999"})
        assert "No booking found" in result
