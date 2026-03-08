"""Booking Agent — Handles all reservation-related guest queries."""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from hotel_agent.config import settings
from hotel_agent.tools.booking_tools import (
    cancel_booking,
    check_availability,
    create_booking,
    modify_booking,
)
from hotel_agent.tools.knowledge_base import search_hotel_info

BOOKING_SYSTEM_PROMPT = """\
You are the Booking Specialist at Grand Horizon Hotel. You help guests with:

- Checking room availability and prices
- Making new reservations
- Modifying existing bookings (dates, room type)
- Cancelling reservations

## Guidelines
- Always confirm details before making a booking (guest name, room type, dates)
- Mention the cancellation policy: free up to 48 hours before check-in
- If a guest asks about room types without specific dates, describe options and ask for dates
- Use the tools provided to check real availability and create bookings
- Be warm, professional, and proactive — suggest upgrades when appropriate
- Today's date is 2026-03-01 for reference

## Room Types Available
- Standard Room: $149/night (2 guests)
- Deluxe Room: $219/night (3 guests)
- Premium Suite: $349/night (4 guests)
- Family Suite: $299/night (5 guests)
- Penthouse Suite: $599/night (4 guests)
- Accessible Room: $149/night (2 guests)
"""


def get_booking_agent() -> ChatOpenAI:
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
    return llm.bind_tools([
        check_availability,
        create_booking,
        cancel_booking,
        modify_booking,
        search_hotel_info,
    ])


def get_booking_system_message() -> SystemMessage:
    return SystemMessage(content=BOOKING_SYSTEM_PROMPT)
