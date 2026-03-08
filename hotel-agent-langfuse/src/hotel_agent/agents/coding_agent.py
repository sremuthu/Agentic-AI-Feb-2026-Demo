"""Coding Agent — Template/Response builder for structured guest communications.

Responsibilities:
- Generates structured responses (booking confirmations, bill summaries)
- Builds dynamic response templates based on context
- Formats raw tool output into guest-friendly messages
- Generates email-style confirmations when needed
"""

from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from hotel_agent.config import settings

logger = logging.getLogger(__name__)

CODING_SYSTEM_PROMPT = """\
You are a response formatting agent for Grand Horizon Hotel.

Your job is to take raw data from hotel systems and format it into polished,
guest-friendly messages. You create:

1. **Booking Confirmations** — formatted with all key details
2. **Bill Summaries** — clear, itemized, easy to read
3. **Email Templates** — professional hotel communications
4. **Information Cards** — formatted facility/amenity information

Rules:
- Use a warm, professional hospitality tone
- Include all relevant details (dates, prices, policies)
- Add helpful tips where appropriate (e.g. "Remember, free cancellation up to 48h before check-in")
- Structure with clear headings and bullet points
- Never fabricate information — only format what is provided

Respond with the formatted message only. No JSON wrapper needed.
"""


def get_coding_agent() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )


async def format_response(
    raw_data: str,
    template_type: str = "general",
    guest_name: str = "",
) -> str:
    """Format raw system data into a polished guest-facing message.

    Args:
        raw_data: Raw output from tools or agents.
        template_type: One of 'booking_confirmation', 'bill_summary', 'email', 'info_card', 'general'.
        guest_name: Guest name for personalization.
    """
    llm = get_coding_agent()

    prompt = (
        f"## Template Type: {template_type}\n"
        f"## Guest Name: {guest_name or 'Valued Guest'}\n\n"
        f"## Raw Data to Format:\n{raw_data}\n\n"
        f"Please format this into a polished, guest-friendly message."
    )

    result = await llm.ainvoke([
        SystemMessage(content=CODING_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    return result.content
