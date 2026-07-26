"""Force rebuild ChromaDB from knowledge_base/*.md using Gemini embeddings."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.vector_store import reset_vector_store


def main() -> int:
    vs = reset_vector_store(force_reindex=True)
    print(vs.status())
    if vs.status().get("backend") != "chromadb":
        print("\nWARNING: ChromaDB not active — install: pip install chromadb")
        return 1
    print("\n✓ RAG reindexed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
