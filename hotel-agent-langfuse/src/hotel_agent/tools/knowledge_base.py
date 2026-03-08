"""RAG retrieval tool — searches hotel knowledge base via ChromaDB."""

from __future__ import annotations

from langchain_core.tools import tool

from hotel_agent.knowledge.vectorstore import search


@tool
def search_hotel_info(query: str) -> str:
    """Search the hotel knowledge base for relevant information about policies, rooms, facilities, or FAQs.

    Args:
        query: The guest's question or topic to search for.
    """
    results = search(query, n_results=3)

    if not results:
        return "No relevant information found in the hotel knowledge base."

    sections = []
    for hit in results:
        category = hit["metadata"].get("category", "unknown")
        section = hit["metadata"].get("section", "")
        label = f"[{category}]" + (f" {section}" if section else "")
        sections.append(f"--- {label} ---\n{hit['content']}")

    return "\n\n".join(sections)
