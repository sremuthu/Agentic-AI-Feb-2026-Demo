"""Tests for the Router Agent — intent classification accuracy."""

import pytest
from unittest.mock import AsyncMock, patch

from hotel_agent.models.schemas import Intent, RouterClassification


BOOKING_QUERIES = [
    "I want to book a deluxe room for March 15-18",
    "Do you have any rooms available this weekend?",
    "I need to cancel my reservation BK-1001",
    "Can I change my check-in date to March 20?",
    "How much is the penthouse suite per night?",
]

AMENITIES_QUERIES = [
    "What time does the pool close?",
    "Do you have a gym?",
    "Is there a spa at the hotel?",
    "What are the restaurant hours?",
    "Is Wi-Fi included in the room?",
]

BILLING_QUERIES = [
    "I was charged twice for room service",
    "Can I see my bill?",
    "I have a promo code WELCOME10",
    "I need a refund for the mini-bar charges",
    "What payment methods do you accept?",
]

COMPLAINT_QUERIES = [
    "The AC in my room isn't working",
    "My room hasn't been cleaned yet and it's 3 PM",
    "The staff at the front desk was very rude to me",
    "There's been loud construction noise all morning",
    "I found a cockroach in my bathroom",
]

GENERAL_QUERIES = [
    "What is the Wi-Fi password?",
    "Do you have a loyalty program?",
    "Where can I store my luggage after checkout?",
    "What's the minimum age for check-in?",
    "Can I host a wedding at the hotel?",
]


@pytest.mark.asyncio
@patch("hotel_agent.agents.router.get_router_llm")
async def test_booking_intent(mock_llm):
    """Test that booking queries are classified correctly."""
    from hotel_agent.agents.router import classify_intent

    mock_response = AsyncMock()
    mock_response.content = '{"intent": "booking", "confidence": 0.95, "reasoning": "Guest wants to book a room"}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

    result = await classify_intent("I want to book a deluxe room for March 15-18")
    assert result.intent == Intent.BOOKING
    assert result.confidence >= 0.8


@pytest.mark.asyncio
@patch("hotel_agent.agents.router.get_router_llm")
async def test_complaint_intent(mock_llm):
    """Test that complaints are classified correctly."""
    from hotel_agent.agents.router import classify_intent

    mock_response = AsyncMock()
    mock_response.content = '{"intent": "complaint", "confidence": 0.92, "reasoning": "Guest has an issue"}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

    result = await classify_intent("The AC in my room isn't working")
    assert result.intent == Intent.COMPLAINT


@pytest.mark.asyncio
@patch("hotel_agent.agents.router.get_router_llm")
async def test_fallback_on_parse_error(mock_llm):
    """Test that parse errors fall back to general intent."""
    from hotel_agent.agents.router import classify_intent

    mock_response = AsyncMock()
    mock_response.content = "This is not valid JSON at all"
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

    result = await classify_intent("random gibberish")
    assert result.intent == Intent.GENERAL
    assert result.confidence < 0.5


@pytest.mark.asyncio
@patch("hotel_agent.agents.router.get_router_llm")
async def test_amenities_intent(mock_llm):
    """Test amenities classification."""
    from hotel_agent.agents.router import classify_intent

    mock_response = AsyncMock()
    mock_response.content = '{"intent": "amenities", "confidence": 0.90, "reasoning": "Asking about pool"}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

    result = await classify_intent("What time does the pool close?")
    assert result.intent == Intent.AMENITIES


@pytest.mark.asyncio
@patch("hotel_agent.agents.router.get_router_llm")
async def test_billing_intent(mock_llm):
    """Test billing classification."""
    from hotel_agent.agents.router import classify_intent

    mock_response = AsyncMock()
    mock_response.content = '{"intent": "billing", "confidence": 0.88, "reasoning": "Billing inquiry"}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)

    result = await classify_intent("Can I see my bill?")
    assert result.intent == Intent.BILLING
