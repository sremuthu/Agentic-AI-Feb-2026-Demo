"""LLM-as-judge evaluation pipeline for response quality monitoring."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI

from langfuse.api.client import FernLangfuse

from hotel_agent.config import settings
from hotel_agent.models.schemas import EvaluationScore
from hotel_agent.observability.tracing import score_trace


def _get_langfuse_api() -> FernLangfuse:
    return FernLangfuse(
        base_url=settings.langfuse_host,
        username=settings.langfuse_public_key,
        password=settings.langfuse_secret_key,
    )

logger = logging.getLogger(__name__)

EVALUATION_PROMPT = """\
You are an expert quality evaluator for a hotel customer care AI system.

Evaluate the AI assistant's response to a hotel guest query.

## Guest Query
{query}

## AI Response
{response}

## Context Retrieved (RAG)
{context}

## Evaluation Criteria

Rate each dimension from 1-5:

1. **Helpfulness** (1-5): Does the response directly address the guest's need? Does it provide actionable information?
   - 1: Completely unhelpful / irrelevant
   - 3: Partially addresses the query
   - 5: Fully addresses the query with clear next steps

2. **Accuracy** (1-5): Is the information factually correct based on hotel policies and data?
   - 1: Contains major factual errors
   - 3: Mostly correct with minor issues
   - 5: Fully accurate, consistent with hotel data

3. **Tone** (1-5): Is the response professional, warm, and appropriate for hospitality?
   - 1: Rude, cold, or inappropriate
   - 3: Acceptable but could be more welcoming
   - 5: Warm, professional, empathetic — excellent hospitality tone

Respond in JSON format:
{{
    "helpfulness": <1-5>,
    "accuracy": <1-5>,
    "tone": <1-5>,
    "reasoning": "<brief explanation>"
}}
"""


async def evaluate_response(
    query: str,
    response: str,
    context: str = "",
    trace_id: str | None = None,
) -> EvaluationScore:
    """Run LLM-as-judge evaluation on a single query-response pair."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Use cheaper model for evals
        api_key=settings.openai_api_key,
        temperature=0,
    )

    prompt = EVALUATION_PROMPT.format(
        query=query,
        response=response,
        context=context or "No context retrieved",
    )

    result = await llm.ainvoke(prompt)
    content = result.content.strip()

    # Parse JSON from response
    try:
        # Handle markdown code blocks
        if "```" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
            if not content:
                content = result.content.split("```")[-2].strip()
        data = json.loads(content)
    except (json.JSONDecodeError, IndexError):
        logger.warning("Failed to parse evaluation response: %s", content)
        data = {"helpfulness": 3, "accuracy": 3, "tone": 3, "reasoning": "Parse error in evaluation"}

    score = EvaluationScore(**data)

    # Push scores to Langfuse if trace_id provided
    if trace_id:
        score_trace(trace_id, "eval_helpfulness", float(score.helpfulness), score.reasoning)
        score_trace(trace_id, "eval_accuracy", float(score.accuracy), score.reasoning)
        score_trace(trace_id, "eval_tone", float(score.tone), score.reasoning)
        avg = (score.helpfulness + score.accuracy + score.tone) / 3
        score_trace(trace_id, "eval_overall", round(avg, 2), score.reasoning)

    return score


async def batch_evaluate(trace_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch traces from Langfuse and evaluate each one. Returns summary."""
    lf_api = _get_langfuse_api()
    results = []

    for tid in trace_ids:
        try:
            obs_page = lf_api.observations.get_many(trace_id=tid)
            obs_list = obs_page.data or []

            # Router span holds the raw user query as input
            router_obs = next((o for o in obs_list if o.name == "router" and o.input), None)
            # Specialist agent span output is a dict with a "response" key
            specialist_obs = next(
                (o for o in obs_list if o.name and o.name.startswith("specialist_") and o.output),
                None,
            )

            if not router_obs or not specialist_obs:
                continue

            query = str(router_obs.input)
            # Output is a dict like {'response': '...'}; extract the text
            raw_output = specialist_obs.output
            if isinstance(raw_output, dict):
                response = str(raw_output.get("response", raw_output))
            else:
                response = str(raw_output)

            score = await evaluate_response(
                query=query,
                response=response,
                trace_id=tid,
            )
            results.append({
                "trace_id": tid,
                "helpfulness": score.helpfulness,
                "accuracy": score.accuracy,
                "tone": score.tone,
                "reasoning": score.reasoning,
            })
        except Exception as exc:
            logger.error("Evaluation failed for trace %s: %s", tid, exc)
            results.append({"trace_id": tid, "error": str(exc)})

    return results
