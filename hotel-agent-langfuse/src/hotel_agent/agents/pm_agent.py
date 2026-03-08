"""PM Agent — Project Manager that orchestrates the guest interaction lifecycle.

Responsibilities:
- Manages session state and conversation flow
- Tracks query resolution status and SLA compliance
- Decides when to escalate to human operators
- Coordinates handoffs between specialist agents
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from hotel_agent.config import settings
from hotel_agent.models.schemas import AgentState, QueryStatus

logger = logging.getLogger(__name__)

PM_SYSTEM_PROMPT = """\
You are the Project Manager agent for Grand Horizon Hotel's customer care system.

Your responsibilities:
1. ASSESS each guest interaction for urgency and complexity
2. TRACK resolution status — mark queries as open, in_progress, resolved, or escalated
3. DECIDE if a query needs human escalation based on:
   - Guest frustration level (repeated complaints, aggressive language)
   - Legal/safety concerns
   - Financial disputes over $500
   - Issues the specialist agent couldn't resolve
4. COORDINATE multi-step requests that span multiple departments
5. ENSURE SLA compliance — flag queries that have been open too long

After the specialist agent responds, you provide a brief status assessment:
- Is the query resolved? Partially resolved? Needs follow-up?
- Should this be escalated?
- What is the overall guest sentiment?

Respond ONLY with a JSON object:
{
    "query_status": "resolved" | "in_progress" | "escalated",
    "needs_escalation": true/false,
    "escalation_reason": "reason or null",
    "guest_sentiment": "positive" | "neutral" | "negative" | "frustrated",
    "follow_up_needed": true/false,
    "notes": "brief assessment"
}
"""


def get_pm_agent() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


async def assess_interaction(
    state: AgentState,
    specialist_response: str,
) -> dict[str, Any]:
    """PM agent assesses the interaction after a specialist responds."""
    llm = get_pm_agent()

    messages_summary = ""
    for msg in state["messages"][-4:]:  # Last few messages for context
        role = "Guest" if msg.type == "human" else "Agent"
        messages_summary += f"{role}: {msg.content}\n"

    assessment_input = (
        f"## Conversation Context\n{messages_summary}\n\n"
        f"## Specialist Response\n{specialist_response}\n\n"
        f"## Query Details\n"
        f"- Intent: {state.get('intent', 'unknown')}\n"
        f"- Agent used: {state.get('current_agent', 'unknown')}\n"
        f"- Session: {state.get('session_id', 'unknown')}\n"
    )

    result = await llm.ainvoke([
        SystemMessage(content=PM_SYSTEM_PROMPT),
        AIMessage(content=assessment_input),
    ])

    import json
    try:
        content = result.content.strip()
        if "```" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        assessment = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        logger.warning("PM agent response parse error: %s", result.content)
        assessment = {
            "query_status": "resolved",
            "needs_escalation": False,
            "escalation_reason": None,
            "guest_sentiment": "neutral",
            "follow_up_needed": False,
            "notes": "Assessment unavailable",
        }

    return assessment
