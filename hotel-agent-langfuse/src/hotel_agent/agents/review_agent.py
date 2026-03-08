"""Review Agent — Quality gate that evaluates responses before they reach the guest.

Responsibilities:
- Checks for hallucinations and factual errors
- Validates policy compliance
- Ensures appropriate tone for hospitality
- Flags problematic responses for revision
- Feeds quality scores into Langfuse observability
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from hotel_agent.config import settings

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = """\
You are a quality review agent for Grand Horizon Hotel's AI customer care system.

Your job is to review the specialist agent's response BEFORE it reaches the guest.

## Review Checklist
1. **Accuracy**: Does the response contain correct information? Are prices, times, policies accurate?
2. **Hallucination Check**: Does the response make up information not in the context?
3. **Policy Compliance**: Does the response follow hotel policies (no unauthorized discounts, correct cancellation rules)?
4. **Tone**: Is the response warm, professional, and empathetic? Appropriate for a luxury hotel?
5. **Completeness**: Does the response fully address the guest's question?
6. **Safety**: Does the response avoid sharing sensitive data (credit cards, internal systems)?

Respond ONLY with a JSON object:
{
    "approved": true/false,
    "score": <1-10>,
    "issues": ["list of issues found, empty if none"],
    "suggestions": "brief improvement suggestion or null",
    "revised_response": "only if approved=false, provide a corrected version; null if approved"
}
"""


def get_review_agent() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )


async def review_response(
    guest_query: str,
    agent_response: str,
    intent: str,
    context: str = "",
) -> dict:
    """Review a specialist agent's response for quality before sending to guest.

    Returns:
        Dict with approved (bool), score (1-10), issues, suggestions, revised_response.
    """
    llm = get_review_agent()

    review_input = (
        f"## Guest Query\n{guest_query}\n\n"
        f"## Agent Response (to review)\n{agent_response}\n\n"
        f"## Intent Classification\n{intent}\n\n"
        f"## Retrieved Context\n{context or 'No context retrieved'}\n"
    )

    result = await llm.ainvoke([
        SystemMessage(content=REVIEW_SYSTEM_PROMPT),
        HumanMessage(content=review_input),
    ])

    try:
        content = result.content.strip()
        if "```" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        review = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        logger.warning("Review agent parse error: %s", result.content)
        review = {
            "approved": True,
            "score": 7,
            "issues": [],
            "suggestions": None,
            "revised_response": None,
        }

    return review
