"""Local embedding models (sentence-transformers on CPU) behind one small interface.

``EMBEDDING_BACKEND=hashing`` swaps in a deterministic feature-hashing embedder
so tests run without downloading a model; it is not meant for real retrieval.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import threading
from functools import lru_cache
from typing import Protocol

from app.config import get_settings
from app.services.knowledge.text import words

logger = logging.getLogger(__name__)

DIMENSIONS = 384


def use_model_cache_dir() -> None:
    """Point Hugging Face at HF_HOME from .env before the library is first imported."""
    home = get_settings().hf_home
    if home:
        os.environ.setdefault("HF_HOME", home)


class Embedder(Protocol):
    model_name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        use_model_cache_dir()
        from sentence_transformers import SentenceTransformer  # heavy import, lazy

        self.model_name = model_name
        self._model = SentenceTransformer(model_name, device="cpu")
        get_dim = getattr(self._model, "get_embedding_dimension", None) or (
            self._model.get_sentence_embedding_dimension
        )
        self.dim = int(get_dim())
        self._lock = threading.Lock()
        if self.dim != DIMENSIONS:
            raise RuntimeError(
                f"{model_name} produces {self.dim}-d vectors but the embeddings column is "
                f"VECTOR({DIMENSIONS}); change the column and re-embed first."
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with self._lock:  # the model is not re-entrant across threads
            vectors = self._model.encode(
                texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False
            )
        return [v.astype(float).tolist() for v in vectors]


class HashingEmbedder:
    """Bag-of-words feature hashing, L2-normalised. Deterministic, dependency-free."""

    model_name = "hashing-384"
    dim = DIMENSIONS

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in words(text):
                h = int(hashlib.md5(token.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0 if (h >> 9) & 1 else -1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embedding_backend == "hashing":
        return HashingEmbedder()
    logger.info("loading embedding model %s", settings.embedding_model)
    return SentenceTransformerEmbedder(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return get_embedder().embed(texts)


def embed_query(text: str) -> list[float]:
    return get_embedder().embed([text])[0]
