"""Tests for specialist agents and project-level agents."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from hotel_agent.models.schemas import Intent


@pytest.mark.asyncio
@patch("hotel_agent.agents.review_agent.get_review_agent")
async def test_review_agent_approves_good_response(mock_llm):
    """Test that review agent approves a well-formed response."""
    from hotel_agent.agents.review_agent import review_response

    mock_response = AsyncMock()
    mock_response.content = '{"approved": true, "score": 9, "issues": [], "suggestions": null, "revised_response": null}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

    result = await review_response(
        guest_query="What time is checkout?",
        agent_response="Check-out time is 11:00 AM. Late check-out is available until 2:00 PM for a $50 fee.",
        intent="amenities",
    )

    assert result["approved"] is True
    assert result["score"] >= 8


@pytest.mark.asyncio
@patch("hotel_agent.agents.review_agent.get_review_agent")
async def test_review_agent_rejects_bad_response(mock_llm):
    """Test that review agent catches a problematic response."""
    from hotel_agent.agents.review_agent import review_response

    mock_response = AsyncMock()
    mock_response.content = '{"approved": false, "score": 3, "issues": ["Incorrect pricing"], "suggestions": "Fix the price", "revised_response": "The standard room is $149/night."}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

    result = await review_response(
        guest_query="How much is a standard room?",
        agent_response="The standard room is $99/night.",
        intent="booking",
    )

    assert result["approved"] is False
    assert result["revised_response"] is not None


@pytest.mark.asyncio
@patch("hotel_agent.agents.pm_agent.get_pm_agent")
async def test_pm_agent_resolves_simple_query(mock_llm):
    """Test PM agent marks a simple query as resolved."""
    from hotel_agent.agents.pm_agent import assess_interaction
    from langchain_core.messages import HumanMessage, AIMessage

    mock_response = AsyncMock()
    mock_response.content = '{"query_status": "resolved", "needs_escalation": false, "escalation_reason": null, "guest_sentiment": "positive", "follow_up_needed": false, "notes": "Simple info query resolved"}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

    state = {
        "messages": [
            HumanMessage(content="What time is checkout?"),
            AIMessage(content="Check-out is at 11:00 AM."),
        ],
        "intent": "amenities",
        "current_agent": "amenities_agent",
        "session_id": "test-session",
        "confidence": 0.95,
        "user_id": "test",
        "query_status": "in_progress",
        "metadata": {},
        "review_passed": True,
        "trace_id": "test-trace",
    }

    result = await assess_interaction(state, "Check-out is at 11:00 AM.")
    assert result["query_status"] == "resolved"
    assert result["needs_escalation"] is False


def test_db_agent_health():
    """Test DB agent reports health correctly."""
    from hotel_agent.agents.db_agent import db_agent

    health = db_agent.check_health()
    assert health["bookings_loaded"] > 0
    assert health["bills_loaded"] > 0
    assert health["rooms_configured"] > 0


def test_db_agent_get_booking():
    """Test DB agent retrieves bookings."""
    from hotel_agent.agents.db_agent import db_agent

    booking = db_agent.get_booking("BK-1001")
    assert booking is not None
    assert booking["guest_name"] == "Alice Johnson"

    missing = db_agent.get_booking("BK-9999")
    assert missing is None


def test_db_agent_list_bookings():
    """Test DB agent lists bookings with filters."""
    from hotel_agent.agents.db_agent import db_agent

    all_bookings = db_agent.list_bookings()
    assert len(all_bookings) >= 3

    alice = db_agent.list_bookings(guest_name="Alice")
    assert len(alice) == 1

    confirmed = db_agent.list_bookings(status="confirmed")
    assert all(b["status"] == "confirmed" for b in confirmed)


def test_mcp_agent_registration():
    """Test MCP agent registers and discovers tools."""
    from hotel_agent.agents.mcp_agent import mcp_agent, register_all_tools, ToolDefinition

    # Register a test tool
    mcp_agent.register_tool(ToolDefinition(
        name="test_tool",
        description="A test tool",
        category="test",
    ))

    tools = mcp_agent.discover_tools(category="test")
    assert len(tools) == 1
    assert tools[0].name == "test_tool"

    # Test usage tracking
    mcp_agent.record_usage("test_tool")
    stats = mcp_agent.get_usage_stats()
    assert stats["test_tool"] == 1

    # Test disable/enable
    mcp_agent.disable_tool("test_tool")
    assert len(mcp_agent.discover_tools(category="test", enabled_only=True)) == 0

    mcp_agent.enable_tool("test_tool")
    assert len(mcp_agent.discover_tools(category="test", enabled_only=True)) == 1
