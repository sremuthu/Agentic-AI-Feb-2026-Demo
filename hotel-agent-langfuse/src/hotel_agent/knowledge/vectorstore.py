"""ChromaDB vector store for hotel knowledge base (RAG)."""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from hotel_agent.config import settings

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

COLLECTION_NAME = "hotel_knowledge"
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "hotel_knowledge"


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        db_path = Path(__file__).resolve().parents[3] / "chroma_db"
        _client = chromadb.PersistentClient(path=str(db_path))
    return _client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = get_client()
        embedding_fn = OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small",
        )
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_fn,
        )
    return _collection


def seed_knowledge_base() -> int:
    """Load all markdown files from data/hotel_knowledge/ into ChromaDB."""
    collection = get_collection()

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for md_file in sorted(DATA_DIR.glob("*.md")):
        content = md_file.read_text()
        category = md_file.stem  # e.g. "policies", "rooms"

        # Split into sections by ## headings
        chunks = _split_into_chunks(content, category)
        for i, (chunk_text, chunk_meta) in enumerate(chunks):
            doc_id = f"{category}_{i}"
            documents.append(chunk_text)
            metadatas.append(chunk_meta)
            ids.append(doc_id)

    if documents:
        # Upsert to handle re-seeding
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    return len(documents)


def search(query: str, n_results: int = 3) -> list[dict]:
    """Search the hotel knowledge base and return relevant chunks."""
    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=n_results)

    hits = []
    for i in range(len(results["documents"][0])):
        hits.append({
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })
    return hits


def _split_into_chunks(content: str, category: str) -> list[tuple[str, dict]]:
    """Split markdown content into chunks by ## section headings."""
    chunks: list[tuple[str, dict]] = []
    current_section = ""
    current_text_lines: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## "):
            # Save previous section
            if current_text_lines:
                text = "\n".join(current_text_lines).strip()
                if text:
                    chunks.append((text, {"category": category, "section": current_section}))
            current_section = line.lstrip("# ").strip()
            current_text_lines = [line]
        else:
            current_text_lines.append(line)

    # Last section
    if current_text_lines:
        text = "\n".join(current_text_lines).strip()
        if text:
            chunks.append((text, {"category": category, "section": current_section}))

    # If no ## headings found, use the whole document as one chunk
    if not chunks:
        chunks.append((content.strip(), {"category": category, "section": "full"}))

    return chunks
