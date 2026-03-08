"""Seed the ChromaDB vector store with hotel knowledge base data."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv
load_dotenv()

from hotel_agent.knowledge.vectorstore import seed_knowledge_base, DATA_DIR


def main():
    print(f"Seeding knowledge base from: {DATA_DIR}")

    md_files = list(DATA_DIR.glob("*.md"))
    print(f"Found {len(md_files)} markdown files: {[f.name for f in md_files]}")

    count = seed_knowledge_base()
    print(f"Indexed {count} document chunks into ChromaDB")
    print("Done! Knowledge base is ready.")


if __name__ == "__main__":
    main()
