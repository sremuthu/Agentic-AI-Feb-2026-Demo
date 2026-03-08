"""Amenities Agent — Provides information about hotel facilities and services."""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from hotel_agent.config import settings
from hotel_agent.tools.knowledge_base import search_hotel_info

AMENITIES_SYSTEM_PROMPT = """\
You are the Amenities & Facilities Specialist at Grand Horizon Hotel. You help guests with:

- Room amenities and features for each room type
- Hotel facilities: pool, gym, spa, restaurant, bar, business center
- Services: room service, concierge, laundry, Wi-Fi, parking
- Operating hours and pricing for facilities
- Kids' club and family services

## Guidelines
- Search the hotel knowledge base for accurate, up-to-date information
- Be enthusiastic about the hotel's offerings — make them sound appealing
- If you don't have specific information, offer to connect the guest with the concierge
- Proactively mention related amenities (e.g., if they ask about the pool, mention the poolside bar)
- Always include hours of operation and pricing when relevant
"""


def get_amenities_agent() -> ChatOpenAI:
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
    return llm.bind_tools([search_hotel_info])


def get_amenities_system_message() -> SystemMessage:
    return SystemMessage(content=AMENITIES_SYSTEM_PROMPT)
