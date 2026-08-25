"""Local embeddings + vector store (FAISS with numpy fallback).

Real model: sentence-transformers (multilingual) when installed (see
requirements-llm.txt). Otherwise a deterministic hashing embedder keeps the
module fully runnable offline / in CI. FAISS is used when available; otherwise
brute-force cosine/L2 search over an in-memory numpy matrix.
"""
from __future__ import annotations

import hashlib
import os
import pickle
import re
from typing import Any, Dict, List, Optional

import numpy as np

EMBED_DIM = 256


class LocalEmbedder:
    def __init__(self) -> None:
        self.dim = EMBED_DIM
        self._st = True  # None = not tried, False = unavailable, else model

    def _maybe_load(self) -> None:
        if self._st is not True:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._st = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            self.dim = self._st.get_sentence_embedding_dimension()
        except Exception:
            self._st = False

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

    # ---- write ----
    def add(self, vectors: np.ndarray, ids: List[str], metas: List[Dict[str, Any]]) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.shape[1] != self.dim:
            self.dim = vectors.shape[1]
        if self._index is None:
            self._ensure_index(self.dim)
        self.ids.extend(ids)
        self.meta.extend(metas)
        self._np = (
            np.concatenate([self._np, vectors], axis=0)
            if self._np.shape[0]
            else vectors
        )
        if self._index is not None:
            self._index.add(vectors)
        self._save()

    # ---- read ----
    def search(self, q: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        q = np.asarray(q, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        if self._np.shape[0] == 0:
            return []
        if self._index is not None:
            k = min(top_k, self._np.shape[0])
            D, I = self._index.search(q, k)
            out = []
            for dist, idx in zip(D[0], I[0]):
                if idx < 0:
                    continue
                out.append(
                    {"id": self.ids[idx], "metadata": self.meta[idx], "score": float(1.0 / (1.0 + dist))}
                )
            return out
        sims = self._np @ q[0]
        k = min(top_k, len(sims))
        top = np.argsort(-sims)[:k]
        return [
            {"id": self.ids[i], "metadata": self.meta[i], "score": float(sims[i])}
            for i in top
        ]

    # ---- persistence ----
    def _save(self) -> None:
        try:
            with open(self.path, "wb") as f:
                pickle.dump(
                    {"dim": self.dim, "ids": self.ids, "meta": self.meta, "np": self._np}, f
                )
        except Exception:
            pass

    def _load(self) -> None:
        try:
            with open(self.path, "rb") as f:
                d = pickle.load(f)
            self.dim = d["dim"]
            self.ids = d["ids"]
            self.meta = d["meta"]
            self._np = d["np"]
        except Exception:
            pass


embedder = LocalEmbedder()
store = VectorStore()
