"""Local embeddings + vector store (FAISS with numpy fallback).

Real model: sentence-transformers (multilingual) when installed (see
requirements-llm.txt). Otherwise a deterministic hashing embedder keeps the
module fully runnable offline / in CI. FAISS is used when available; otherwise
brute-force cosine search over an in-memory numpy matrix.

Documents are keyed by ``doc_id`` and upsert semantics apply: re-adding an
existing id replaces its vector and metadata instead of appending a duplicate.
"""
from __future__ import annotations

import hashlib
import logging
import os
import pickle
import re
import threading
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("embeddings")

EMBED_DIM = 256


class LocalEmbedder:
    def __init__(self) -> None:
        self.dim = EMBED_DIM
        self._st = True  # None = not tried, False = unavailable, else model
        self._model_name = os.getenv("EMBEDDINGS_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

    def _maybe_load(self) -> None:
        if self._st is not True:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._st = SentenceTransformer(self._model_name)
            self.dim = self._st.get_sentence_embedding_dimension()
            logger.info("Embeddings: loaded %s (dim=%d)", self._model_name, self.dim)
        except Exception as exc:
            self._st = False
            logger.warning(
                "Embeddings: sentence-transformers unavailable (%s); "
                "falling back to hashing embedder — vectors are NOT semantic",
                exc,
            )

    @property
    def is_semantic(self) -> bool:
        self._maybe_load()
        return bool(self._st)

    def embed(self, texts: List[str]) -> np.ndarray:
        self._maybe_load()
        if self._st:
            arr = self._st.encode(texts, normalize_embeddings=True)
            return np.asarray(arr, dtype=np.float32)
        return self._hash_embed(texts)

    def _hash_embed(self, texts: List[str]) -> np.ndarray:
        X = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            toks = set(re.findall(r"\w+", t.lower()))
            for tok in toks:
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                X[i, h % self.dim] += 1.0
            norm = np.linalg.norm(X[i])
            if norm > 0:
                X[i] /= norm
        return X


class VectorStore:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.getenv("EMBEDDINGS_PATH", "embeddings_store.pkl")
        self.dim = EMBED_DIM
        self.ids: List[str] = []
        self.meta: List[Dict[str, Any]] = []
        self._np = np.zeros((0, self.dim), dtype=np.float32)
        self._index = None
        self._lock = threading.Lock()
        self._pos: Dict[str, int] = {}
        self._load()

    # ---- FAISS (optional) ----
    def _ensure_index(self, dim: int) -> None:
        try:
            import faiss

            self._index = faiss.IndexFlatL2(dim)
            if self._np.shape[0]:
                self._index.add(self._np)
        except Exception:
            self._index = None

    def _rebuild_index(self) -> None:
        """Recreate the FAISS index from scratch (after removals or a dim change)."""
        self._index = None
        if self._np.shape[0]:
            self._ensure_index(self.dim)

    # ---- write ----
    def add(self, vectors: np.ndarray, ids: List[str], metas: List[Dict[str, Any]]) -> Dict[str, int]:
        """Insert or replace documents by id. Returns inserted/updated counts."""
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.shape[1] != self.dim:
            self.dim = vectors.shape[1]
            self._rebuild_index()

        inserted = 0
        updated = 0
        with self._lock:
            for vec, doc_id, meta in zip(vectors, ids, metas):
                pos = self._pos.get(doc_id)
                if pos is None:
                    pos = len(self.ids)
                    self._pos[doc_id] = pos
                    self.ids.append(doc_id)
                    self.meta.append(meta)
                    self._np = (
                        np.concatenate([self._np, vec.reshape(1, -1)], axis=0)
                        if self._np.shape[0]
                        else vec.reshape(1, -1).copy()
                    )
                    if self._index is not None:
                        self._index.add(vec.reshape(1, -1))
                    inserted += 1
                else:
                    # Upsert: replace in place. A flat FAISS index has no update,
                    # so rebuild it to keep search results consistent.
                    self._np[pos] = vec
                    self.meta[pos] = meta
                    self._rebuild_index()
                    updated += 1
            self._save()
        return {"inserted": inserted, "updated": updated}

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            pos = self._pos.pop(doc_id, None)
            if pos is None:
                return False
            keep = [i for i in range(len(self.ids)) if i != pos]
            self.ids = [self.ids[i] for i in keep]
            self.meta = [self.meta[i] for i in keep]
            self._pos = {doc_id_: i for i, doc_id_ in enumerate(self.ids)}
            self._np = self._np[keep] if keep else np.zeros((0, self.dim), dtype=np.float32)
            self._rebuild_index()
            self._save()
            return True

    def __len__(self) -> int:
        return len(self.ids)

    # ---- read ----
    def search(self, q: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        q = np.asarray(q, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        if self._np.shape[0] == 0 or q.shape[1] != self._np.shape[1]:
            return []
        k = min(top_k, self._np.shape[0])
        if self._index is not None:
            D, I = self._index.search(q, k)
            out = []
            for dist, idx in zip(D[0], I[0]):
                if idx < 0:
                    continue
                out.append(
                    {
                        "id": self.ids[idx],
                        "metadata": self.meta[idx],
                        "score": float(1.0 / (1.0 + dist)),
                    }
                )
            return out
        sims = self._np @ q[0]
        top = np.argsort(-sims)[:k]
        return [
            {"id": self.ids[i], "metadata": self.meta[i], "score": float(sims[i])}
            for i in top
        ]

    def all_documents(self) -> List[Dict[str, Any]]:
        return [
            {"id": doc_id, "metadata": meta}
            for doc_id, meta in zip(self.ids, self.meta)
        ]

    # ---- persistence ----
    def _save(self) -> None:
        try:
            tmp = f"{self.path}.tmp"
            with open(tmp, "wb") as f:
                pickle.dump(
                    {"dim": self.dim, "ids": self.ids, "meta": self.meta, "np": self._np}, f
                )
            os.replace(tmp, self.path)  # atomic: never leave a half-written store
        except Exception as exc:
            logger.warning("Embeddings: failed to persist store: %s", exc)

    def _load(self) -> None:
        try:
            with open(self.path, "rb") as f:
                d = pickle.load(f)
            self.dim = d["dim"]
            self.ids = d["ids"]
            self.meta = d["meta"]
            self._np = d["np"]
            self._pos = {doc_id: i for i, doc_id in enumerate(self.ids)}
            self._rebuild_index()
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.warning("Embeddings: could not load store (%s); starting empty", exc)


embedder = LocalEmbedder()
store = VectorStore()
