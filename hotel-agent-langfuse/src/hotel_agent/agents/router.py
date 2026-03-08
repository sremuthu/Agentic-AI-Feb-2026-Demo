"""Router Agent — Classifies guest intent and routes to the correct specialist agent."""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from hotel_agent.config import settings
from hotel_agent.models.schemas import Intent, RouterClassification

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """\
You are the intent classification router for Grand Horizon Hotel's customer care system.

Classify the guest's message into exactly ONE of these intents:

- **booking**: Reservations, room availability, check-in/check-out, cancellations, modifications
- **amenities**: Room features, hotel facilities (pool, gym, spa, restaurant, Wi-Fi), services info
- **billing**: Charges, payments, refunds, invoices, promo codes, billing disputes
- **complaint**: Problems, issues, dissatisfaction, broken items, noise, staff complaints, escalation requests
- **general**: FAQs, loyalty program, parking, directions, events, anything that doesn't fit above

Respond ONLY with a JSON object:
{
    "intent": "booking" | "amenities" | "billing" | "complaint" | "general",
    "confidence": <0.0-1.0>,
    "reasoning": "brief explanation of why this intent was chosen"
}
"""


def get_router_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


async def classify_intent(user_message: str) -> RouterClassification:
    """Classify a guest message into an intent category."""
    llm = get_router_llm()

    result = await llm.ainvoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ])

    try:
        content = result.content.strip()
        if "```" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        data = json.loads(content)
        return RouterClassification(
            intent=Intent(data["intent"]),
            confidence=float(data.get("confidence", 0.8)),
            reasoning=data.get("reasoning", ""),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("Router parse error (%s), defaulting to general: %s", exc, result.content)
        return RouterClassification(
            intent=Intent.GENERAL,
            confidence=0.3,
            reasoning=f"Parse error — defaulting to general. Raw: {result.content[:100]}",
        )
