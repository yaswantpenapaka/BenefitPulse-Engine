"""
ChromaDB-backed knowledge base with Gemini embeddings + keyword fallback.

Architecture (matches system diagram):
  Knowledge Source (markdown policies)
    → ChromaDB vector store (policy embeddings)
    → Benefit Knowledge Agent + Assistant Agent (RAG retrieval)

Without ChromaDB the chatbot still answers via keyword search over the same
markdown corpus — less accurate ranking, but never empty.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "benefit_policies"
MANIFEST_NAME = "index_manifest.json"


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """Paragraph-aware chunking for policy documents."""
    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 1 <= chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            if len(para) > chunk_size:
                words = para.split()
                buf: list[str] = []
                for w in words:
                    buf.append(w)
                    if sum(len(x) + 1 for x in buf) >= chunk_size:
                        chunks.append(" ".join(buf))
                        buf = buf[-max(1, overlap // 10) :]
                current = " ".join(buf)
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


def _corpus_fingerprint(documents: list[dict[str, Any]], embedding_model: str) -> str:
    h = hashlib.sha256()
    h.update(embedding_model.encode())
    for d in sorted(documents, key=lambda x: x["id"]):
        h.update(d["id"].encode())
        h.update(d["text"].encode())
    return h.hexdigest()[:32]


class VectorStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._collection = None
        self._chroma_client = None
        self._docs: list[dict[str, Any]] = []
        self._ready = False
        self._backend: str = "uninitialized"  # chromadb | keyword
        self._embedding_mode: str = "none"  # gemini | default | none
        self._chunk_count: int = 0
        self._last_error: Optional[str] = None

    def initialize(self, force_reindex: bool = False) -> None:
        """Load knowledge base into ChromaDB (preferred) or in-memory keyword index."""
        self.settings = get_settings()
        kb_dir = Path(self.settings.knowledge_base_dir)
        if not kb_dir.exists():
            self._last_error = f"Knowledge base directory missing: {kb_dir}"
            logger.warning(self._last_error)
            self._ready = True
            self._backend = "empty"
            return

        documents: list[dict[str, Any]] = []
        for path in sorted(kb_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for i, chunk in enumerate(_chunk_text(text)):
                doc_id = hashlib.md5(f"{path.name}:{i}".encode()).hexdigest()
                documents.append(
                    {
                        "id": doc_id,
                        "text": chunk,
                        "source": path.name,
                        "title": path.stem.replace("_", " ").title(),
                        "chunk_index": i,
                    }
                )

        self._docs = documents
        self._chunk_count = len(documents)
        logger.info("Loaded %d knowledge chunks from %s", len(documents), kb_dir)

        chroma_path = Path(self.settings.chroma_dir)
        chroma_path.mkdir(parents=True, exist_ok=True)
        manifest_path = chroma_path / MANIFEST_NAME
        fingerprint = _corpus_fingerprint(documents, self.settings.embedding_model)

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._chroma_client = chromadb.PersistentClient(
                path=str(chroma_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )

            existing = None
            try:
                existing = self._chroma_client.get_collection(COLLECTION_NAME)
            except Exception:
                existing = None

            need_reindex = force_reindex or self.settings.chroma_reindex
            if existing is not None and existing.count() > 0 and not need_reindex:
                if manifest_path.exists():
                    try:
                        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
                        if prev.get("fingerprint") != fingerprint:
                            need_reindex = True
                            logger.info("Knowledge corpus changed — reindexing ChromaDB")
                    except Exception:
                        need_reindex = True
                else:
                    need_reindex = True

            if need_reindex and existing is not None:
                try:
                    self._chroma_client.delete_collection(COLLECTION_NAME)
                except Exception as e:
                    logger.warning("Could not delete old collection: %s", e)
                existing = None

            self._collection = self._chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine", "app": "benefit-activation"},
            )

            if self._collection.count() == 0 and documents:
                embeddings = self._embed_batch([d["text"] for d in documents])
                ids = [d["id"] for d in documents]
                texts = [d["text"] for d in documents]
                metas = [
                    {
                        "source": d["source"],
                        "title": d["title"],
                        "chunk_index": d["chunk_index"],
                    }
                    for d in documents
                ]
                if embeddings:
                    # Chroma batch limit safety
                    batch = 50
                    for i in range(0, len(documents), batch):
                        self._collection.add(
                            ids=ids[i : i + batch],
                            documents=texts[i : i + batch],
                            metadatas=metas[i : i + batch],
                            embeddings=embeddings[i : i + batch],
                        )
                    self._embedding_mode = "gemini"
                    logger.info(
                        "Indexed %d chunks into ChromaDB with Gemini embeddings",
                        len(documents),
                    )
                else:
                    batch = 50
                    for i in range(0, len(documents), batch):
                        self._collection.add(
                            ids=ids[i : i + batch],
                            documents=texts[i : i + batch],
                            metadatas=metas[i : i + batch],
                        )
                    self._embedding_mode = "chroma_default"
                    logger.info(
                        "Indexed %d chunks into ChromaDB (default/local embeddings)",
                        len(documents),
                    )

                manifest_path.write_text(
                    json.dumps(
                        {
                            "fingerprint": fingerprint,
                            "chunk_count": len(documents),
                            "embedding_mode": self._embedding_mode,
                            "embedding_model": self.settings.embedding_model,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            else:
                # Infer embedding mode from prior index
                if self.settings.has_gemini:
                    self._embedding_mode = "gemini_or_cached"
                else:
                    self._embedding_mode = "chroma_default"
                logger.info(
                    "Using existing ChromaDB collection (%d vectors)",
                    self._collection.count(),
                )

            self._backend = "chromadb"
            self._ready = True
            self._last_error = None
            logger.info(
                "RAG ready: backend=chromadb chunks=%d embeddings=%s",
                self._collection.count(),
                self._embedding_mode,
            )
        except Exception as e:
            self._last_error = str(e)
            logger.warning(
                "ChromaDB init failed, using keyword fallback for RAG: %s", e
            )
            self._collection = None
            self._backend = "keyword"
            self._embedding_mode = "none"
            self._ready = True

    def status(self) -> dict[str, Any]:
        count = 0
        if self._collection is not None:
            try:
                count = self._collection.count()
            except Exception:
                count = self._chunk_count
        else:
            count = self._chunk_count
        return {
            "ready": self._ready,
            "backend": self._backend,
            "embedding_mode": self._embedding_mode,
            "chunk_count": count,
            "corpus_docs": self._chunk_count,
            "chroma_dir": self.settings.chroma_dir,
            "has_gemini_embeddings": self.settings.has_gemini,
            "error": self._last_error,
        }

    def _embed_batch(self, texts: list[str]) -> Optional[list[list[float]]]:
        if not self.settings.has_gemini:
            return None
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.settings.google_api_key)
            result: list[list[float]] = []
            for i in range(0, len(texts), 16):
                batch = texts[i : i + 16]
                for t in batch:
                    emb = genai.embed_content(
                        model=self.settings.embedding_model,
                        content=t,
                        task_type="retrieval_document",
                    )
                    result.append(emb["embedding"])
            return result
        except Exception as e:
            logger.warning("Embedding batch failed: %s", e)
            return None

    def _embed_query(self, query: str) -> Optional[list[float]]:
        if not self.settings.has_gemini:
            return None
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.settings.google_api_key)
            emb = genai.embed_content(
                model=self.settings.embedding_model,
                content=query,
                task_type="retrieval_query",
            )
            return emb["embedding"]
        except Exception as e:
            logger.warning("Query embedding failed: %s", e)
            return None

    def query(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        """Retrieve relevant policy chunks (vector first, keyword fallback)."""
        if not self._ready:
            self.initialize()

        if self._collection is not None:
            try:
                q_emb = self._embed_query(query)
                if q_emb:
                    res = self._collection.query(
                        query_embeddings=[q_emb],
                        n_results=min(top_k, max(1, self._collection.count())),
                        include=["documents", "metadatas", "distances"],
                    )
                else:
                    res = self._collection.query(
                        query_texts=[query],
                        n_results=min(top_k, max(1, self._collection.count())),
                        include=["documents", "metadatas", "distances"],
                    )
                results = []
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                dists = (res.get("distances") or [[]])[0]
                for doc, meta, dist in zip(docs, metas, dists):
                    results.append(
                        {
                            "text": doc,
                            "source": (meta or {}).get("source", "unknown"),
                            "title": (meta or {}).get("title", "Policy"),
                            "score": 1.0 - float(dist) if dist is not None else 0.5,
                        }
                    )
                if results:
                    return results
            except Exception as e:
                logger.warning("Vector query failed, keyword fallback: %s", e)

        return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored: list[tuple[float, dict]] = []
        for d in self._docs:
            text_l = d["text"].lower()
            source_l = d["source"].lower()
            score = 0.0
            for tok in tokens:
                if len(tok) < 3:
                    continue
                if tok in text_l:
                    score += text_l.count(tok) * 1.0
                if tok in source_l:
                    score += 3.0
            ql = query.lower()
            if "purchase" in ql and "purchase" in source_l:
                score += 5
            if "return" in ql and "return" in source_l:
                score += 5
            if "travel" in ql or "delay" in ql or "flight" in ql:
                if "travel" in source_l:
                    score += 5
            if "warranty" in ql and "warranty" in source_l:
                score += 5
            if "exclu" in ql and "exclu" in source_l:
                score += 4
            if score > 0:
                scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, d in scored[:top_k]:
            results.append(
                {
                    "text": d["text"],
                    "source": d["source"],
                    "title": d["title"],
                    "score": min(1.0, score / 20.0),
                }
            )
        if not results and self._docs:
            for d in self._docs[:top_k]:
                results.append(
                    {
                        "text": d["text"],
                        "source": d["source"],
                        "title": d["title"],
                        "score": 0.3,
                    }
                )
        return results


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        _vector_store.initialize()
    return _vector_store


def reset_vector_store(force_reindex: bool = False) -> VectorStore:
    """Re-initialize (used by admin reindex script / health repair)."""
    global _vector_store
    _vector_store = VectorStore()
    _vector_store.initialize(force_reindex=force_reindex)
    return _vector_store
