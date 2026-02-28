"""
HR Vector Store — ChromaDB + BM25 hybrid RAG for HR policies.

Policies are stored as LangChain Documents in a persistent ChromaDB collection.
Retrieval uses an EnsembleRetriever (semantic + BM25) with Reciprocal Rank Fusion.

Auto-seeds on first import if the collection is empty.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers.ensemble import EnsembleRetriever

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ─────────────────────────────────────────────
# Policy source data (single source of truth)
# ─────────────────────────────────────────────

HR_POLICIES: dict[str, str] = {
    "remote_work": """Remote Work Policy:
- Employees may work remotely up to 3 days per week
- Remote work requires manager approval for the arrangement
- Core collaboration hours: 10 am–3 pm in your local timezone
- Must be reachable via Slack/Teams during core hours
- Home-office equipment allowance: $500 per year
- VPN must be used when accessing company systems remotely""",

    "leave": """Leave & Time-Off Policy:
- Annual leave: 15 days (accrued monthly, max carry-over 5 days)
- Sick leave: 10 days per year (no carry-over)
- Personal leave: 3 days per year
- Parental leave: 16 weeks fully paid (primary caregiver); 4 weeks (secondary)
- Bereavement: 5 days for immediate family, 3 days for extended family
- Leave requests require at least 2 weeks advance notice (except sick/emergency)
- All requests must be submitted through the HR portal""",

    "performance": """Performance Review Policy:
- Annual reviews held every December
- Mid-year check-ins held every June
- Ratings on a 1–5 scale (1 = Below Expectations, 5 = Exceptional)
- 360-degree feedback collected from peers and direct reports
- Performance Improvement Plans (PIP) issued for ratings below 2
- Merit salary increases tied to performance ratings
- Promotion eligibility reviewed annually""",

    "code_of_conduct": """Code of Conduct:
- Treat all colleagues with respect and professionalism
- Zero tolerance for harassment, discrimination, or bullying
- Conflicts of interest must be disclosed to HR immediately
- Confidential information must never be shared outside authorised channels
- Report violations to HR or the anonymous Ethics Hotline
- Retaliation against anyone who reports in good faith is strictly prohibited
- Violations may result in disciplinary action up to and including termination""",

    "compensation": """Compensation & Benefits Policy:
- Salaries reviewed annually following performance reviews
- Equity grants vest over 4 years with a 1-year cliff
- Health insurance: company covers 90% of premium (employee + dependants)
- 401(k): company matches up to 4% of salary
- Annual learning & development budget: $1,500 per employee
- Gym/wellness reimbursement: $50/month""",
}

POLICY_DESCRIPTIONS: dict[str, str] = {
    "remote_work":     "Remote work days, core hours, equipment allowance",
    "leave":           "Annual, sick, personal, parental, and bereavement leave",
    "performance":     "Review cycle, ratings scale, PIPs, merit increases",
    "code_of_conduct": "Respect, harassment, conflicts of interest, reporting",
    "compensation":    "Salary reviews, equity, health insurance, 401(k), L&D budget",
}

# ─────────────────────────────────────────────
# ChromaDB config
# ─────────────────────────────────────────────

_CHROMA_PATH       = str(Path(__file__).parent / "hr_chroma_db")
_COLLECTION_NAME   = "hr_policies"
_EMBEDDING_MODEL   = "text-embedding-3-small"


def _make_documents() -> list[Document]:
    """Convert the HR_POLICIES dict into LangChain Documents."""
    return [
        Document(
            page_content=f"Topic: {topic}\n\n{text}",
            metadata={"topic": topic, "description": POLICY_DESCRIPTIONS.get(topic, "")},
        )
        for topic, text in HR_POLICIES.items()
    ]


# ─────────────────────────────────────────────
# Vector store init (idempotent)
# ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=_EMBEDDING_MODEL)


def init_vector_store() -> Chroma:
    """Load or create the ChromaDB vector store. Seeds if empty."""
    store = Chroma(
        collection_name=_COLLECTION_NAME,
        embedding_function=_get_embeddings(),
        persist_directory=_CHROMA_PATH,
    )
    # Seed only when the collection is empty
    if store._collection.count() == 0:
        print("[VectorStore] Seeding HR policies into ChromaDB…")
        docs = _make_documents()
        store.add_documents(docs)
        print(f"[VectorStore] Added {len(docs)} policy documents.")
    return store


# ─────────────────────────────────────────────
# Hybrid retriever (Semantic + BM25)
# ─────────────────────────────────────────────

def _get_ensemble_retriever(k: int = 3) -> EnsembleRetriever:
    """Build a hybrid EnsembleRetriever combining Chroma + BM25."""
    store = init_vector_store()
    chroma_retriever = store.as_retriever(search_kwargs={"k": k})

    docs = _make_documents()
    bm25_retriever = BM25Retriever.from_documents(docs)
    bm25_retriever.k = k

    return EnsembleRetriever(
        retrievers=[chroma_retriever, bm25_retriever],
        weights=[0.5, 0.5],
    )


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def search_policies(query: str, k: int = 3) -> list[dict]:
    """Hybrid search over HR policies. Returns up to k results."""
    retriever = _get_ensemble_retriever(k=k)
    results = retriever.invoke(query)
    seen: set[str] = set()
    output: list[dict] = []
    for doc in results:
        topic = doc.metadata.get("topic", "unknown")
        if topic not in seen:
            seen.add(topic)
            output.append({
                "topic":       topic,
                "description": doc.metadata.get("description", ""),
                "content":     HR_POLICIES.get(topic, doc.page_content),
            })
    return output


def get_policy_by_topic(topic: str) -> str | None:
    """Exact topic lookup — returns policy text or None if not found."""
    key = topic.lower().replace(" ", "_")
    # Direct match
    if key in HR_POLICIES:
        return HR_POLICIES[key]
    # Partial match
    for k in HR_POLICIES:
        if key in k or k in key:
            return HR_POLICIES[k]
    return None


def list_policy_topics() -> list[dict]:
    """Return all policy topics with their short descriptions."""
    return [
        {"topic": topic, "description": desc}
        for topic, desc in POLICY_DESCRIPTIONS.items()
    ]
