"""LangGraph workflow — the core multi-agent orchestration graph.

Flow:
  User Message → Router → Specialist Agent → Review → PM Assessment → Response
                                                 ↑
                                          (tool calls loop)

Every node is fully traced via Langfuse for observability.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph

from hotel_agent.agents.amenities import get_amenities_agent, get_amenities_system_message
from hotel_agent.agents.billing import get_billing_agent, get_billing_system_message
from hotel_agent.agents.booking import get_booking_agent, get_booking_system_message
from hotel_agent.agents.complaints import get_complaints_agent, get_complaints_system_message
from hotel_agent.agents.general import get_general_agent, get_general_system_message
from hotel_agent.agents.pm_agent import assess_interaction
from hotel_agent.agents.review_agent import review_response
from hotel_agent.agents.router import classify_intent
from hotel_agent.models.schemas import AgentState, Intent
from hotel_agent.observability.tracing import create_trace, score_trace, traced_span

logger = logging.getLogger(__name__)

# --- Tool execution helpers ---

TOOL_MAP: dict[str, Any] = {}


def _register_tools() -> None:
    """Build a name→callable map for all tools."""
    from hotel_agent.tools.booking_tools import (
        cancel_booking, check_availability, create_booking, modify_booking,
    )
    from hotel_agent.tools.billing_tools import apply_discount, get_bill, process_refund
    from hotel_agent.tools.knowledge_base import search_hotel_info

    for t in [
        check_availability, create_booking, cancel_booking, modify_booking,
        get_bill, process_refund, apply_discount,
        search_hotel_info,
    ]:
        TOOL_MAP[t.name] = t


def _execute_tool_calls(ai_message: AIMessage) -> list[ToolMessage]:
    """Execute all tool calls in an AIMessage and return ToolMessages."""
    if not TOOL_MAP:
        _register_tools()

    results = []
    for tc in ai_message.tool_calls:
        tool_fn = TOOL_MAP.get(tc["name"])
        if tool_fn is None:
            results.append(ToolMessage(
                content=f"Unknown tool: {tc['name']}",
                tool_call_id=tc["id"],
            ))
            continue
        try:
            output = tool_fn.invoke(tc["args"])
            results.append(ToolMessage(content=str(output), tool_call_id=tc["id"]))
        except Exception as exc:
            results.append(ToolMessage(content=f"Tool error: {exc}", tool_call_id=tc["id"]))
    return results


# --- Graph Nodes ---

async def route_node(state: AgentState) -> dict:
    """Classify intent and decide which specialist to route to."""
    last_message = state["messages"][-1]
    user_text = last_message.content if isinstance(last_message, HumanMessage) else str(last_message)

    trace = state["metadata"].get("_trace")
    with traced_span(trace, "router", input_data=user_text) as span_ctx:
        classification = await classify_intent(user_text)
        span_ctx["output"] = {
            "intent": classification.intent.value,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
        }

    # Score the router confidence in Langfuse
    if state.get("trace_id"):
        score_trace(state["trace_id"], "router_confidence", classification.confidence, classification.reasoning)

    return {
        "intent": classification.intent.value,
        "confidence": classification.confidence,
        "current_agent": classification.intent.value,
        "messages": [],  # Don't add messages, just update state
    }


def _get_agent_and_system(intent: str) -> tuple[Any, Any]:
    """Get the specialist agent LLM and system message for an intent."""
    agents = {
        Intent.BOOKING.value: (get_booking_agent, get_booking_system_message),
        Intent.AMENITIES.value: (get_amenities_agent, get_amenities_system_message),
        Intent.BILLING.value: (get_billing_agent, get_billing_system_message),
        Intent.COMPLAINT.value: (get_complaints_agent, get_complaints_system_message),
        Intent.GENERAL.value: (get_general_agent, get_general_system_message),
    }
    get_agent, get_sys = agents.get(intent, agents[Intent.GENERAL.value])
    return get_agent(), get_sys()


async def specialist_node(state: AgentState) -> dict:
    """Run the appropriate specialist agent with tool-calling loop."""
    intent = state["intent"]
    agent_llm, sys_msg = _get_agent_and_system(intent)
    trace = state["metadata"].get("_trace")

    with traced_span(trace, f"specialist_{intent}", input_data=intent) as span_ctx:
        # Build message history with system prompt
        messages = [sys_msg] + list(state["messages"])

        # Tool-calling loop (max 5 iterations to prevent infinite loops)
        for _ in range(5):
            response = await agent_llm.ainvoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            # Execute tool calls
            tool_results = _execute_tool_calls(response)
            messages.extend(tool_results)

        final_content = response.content or "I'm sorry, I couldn't process that request."
        span_ctx["output"] = {"response": final_content, "tool_calls": len(response.tool_calls) if response.tool_calls else 0}

    return {
        "messages": [AIMessage(content=final_content)],
        "current_agent": f"{intent}_agent",
    }


async def review_node(state: AgentState) -> dict:
    """Review agent checks the specialist response before sending to guest."""
    messages = state["messages"]
    last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    last_human = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)

    if not last_ai or not last_human:
        return {"review_passed": True, "messages": []}

    trace = state["metadata"].get("_trace")
    with traced_span(trace, "review", input_data=last_ai.content) as span_ctx:
        review = await review_response(
            guest_query=last_human.content,
            agent_response=last_ai.content,
            intent=state["intent"],
        )
        span_ctx["output"] = review

    # Score in Langfuse
    if state.get("trace_id"):
        score_trace(state["trace_id"], "review_score", float(review.get("score", 7)))

    if not review.get("approved", True) and review.get("revised_response"):
        # Replace the last AI message with the revised version
        return {
            "review_passed": False,
            "messages": [AIMessage(content=review["revised_response"])],
        }

    return {"review_passed": True, "messages": []}


async def pm_node(state: AgentState) -> dict:
    """PM agent assesses the interaction and sets final query status."""
    last_ai = next((m for m in reversed(state["messages"]) if isinstance(m, AIMessage)), None)
    if not last_ai:
        return {"query_status": "resolved", "messages": []}

    trace = state["metadata"].get("_trace")
    with traced_span(trace, "pm_assessment") as span_ctx:
        assessment = await assess_interaction(state, last_ai.content)
        span_ctx["output"] = assessment

    # Score in Langfuse
    if state.get("trace_id"):
        status = assessment.get("query_status", "resolved")
        escalated = 1.0 if assessment.get("needs_escalation") else 0.0
        score_trace(state["trace_id"], "escalated", escalated)
        sentiment_map = {"positive": 1.0, "neutral": 0.5, "negative": 0.25, "frustrated": 0.0}
        sentiment_score = sentiment_map.get(assessment.get("guest_sentiment", "neutral"), 0.5)
        score_trace(state["trace_id"], "guest_sentiment", sentiment_score)

    return {
        "query_status": assessment.get("query_status", "resolved"),
        "messages": [],
    }


# --- Routing Logic ---

def route_to_specialist(state: AgentState) -> str:
    """Conditional edge: always go to specialist after routing."""
    return "specialist"


# --- Build the Graph ---

def build_workflow() -> StateGraph:
    """Construct the LangGraph workflow with all nodes and edges."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("route", route_node)
    graph.add_node("specialist", specialist_node)
    graph.add_node("review", review_node)
    graph.add_node("pm", pm_node)

    # Set entry point
    graph.set_entry_point("route")

    # Edges: route → specialist → review → pm → END
    graph.add_edge("route", "specialist")
    graph.add_edge("specialist", "review")
    graph.add_edge("review", "pm")
    graph.add_edge("pm", END)

    return graph


def compile_workflow():
    """Build and compile the workflow graph."""
    graph = build_workflow()
    return graph.compile()


# Module-level compiled graph
app_graph = compile_workflow()
