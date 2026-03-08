"""Batch evaluation script — fetches recent traces from Langfuse and evaluates them."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv
load_dotenv()

from langfuse.api.client import FernLangfuse

from hotel_agent.observability.evaluation import batch_evaluate
from hotel_agent.observability.tracing import flush
from hotel_agent.config import settings


async def main():
    print("Fetching recent traces from Langfuse...")

    lf_api = FernLangfuse(
        base_url=settings.langfuse_host,
        username=settings.langfuse_public_key,
        password=settings.langfuse_secret_key,
    )

    try:
        traces = lf_api.trace.list(limit=10)
    except Exception as exc:
        print(f"Error fetching traces: {exc}")
        print("Make sure Langfuse is configured and has traces from /chat requests.")
        return

    if not traces.data:
        print("No traces found. Send some queries to /chat first.")
        return

    trace_ids = [t.id for t in traces.data]
    print(f"Found {len(trace_ids)} traces. Running evaluation...")

    results = await batch_evaluate(trace_ids)

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    scores = {"helpfulness": [], "accuracy": [], "tone": []}
    for r in results:
        if "error" in r:
            print(f"  {r['trace_id']}: ERROR - {r['error']}")
            continue

        print(f"\n  Trace: {r['trace_id']}")
        print(f"    Helpfulness: {r['helpfulness']}/5")
        print(f"    Accuracy:    {r['accuracy']}/5")
        print(f"    Tone:        {r['tone']}/5")
        print(f"    Reasoning:   {r['reasoning'][:100]}")

        scores["helpfulness"].append(r["helpfulness"])
        scores["accuracy"].append(r["accuracy"])
        scores["tone"].append(r["tone"])

    if any(scores.values()):
        print("\n" + "-" * 60)
        print("AVERAGES:")
        for dim, vals in scores.items():
            if vals:
                avg = sum(vals) / len(vals)
                print(f"  {dim}: {avg:.1f}/5")
        overall = sum(sum(v) for v in scores.values()) / sum(len(v) for v in scores.values())
        print(f"  OVERALL: {overall:.1f}/5")

    flush()
    print("\nScores pushed to Langfuse. Check your dashboard!")


if __name__ == "__main__":
    asyncio.run(main())
