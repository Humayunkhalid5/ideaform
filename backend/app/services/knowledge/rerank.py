"""Cross-encoder reranking (local, CPU)."""

from __future__ import annotations

import logging
import threading
from functools import lru_cache

from app.config import get_settings
from app.services.knowledge.embeddings import use_model_cache_dir

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        use_model_cache_dir()
        from sentence_transformers import CrossEncoder  # heavy import, lazy

        self.model_name = model_name
        self._model = CrossEncoder(model_name, device="cpu", max_length=512)
        self._lock = threading.Lock()

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        with self._lock:
            scores = self._model.predict([(query, p) for p in passages], show_progress_bar=False)
        return [float(s) for s in scores]


@lru_cache
def get_reranker() -> CrossEncoderReranker | None:
    settings = get_settings()
    if not settings.reranker_enabled:
        return None
    try:
        return CrossEncoderReranker(settings.reranker_model)
    except Exception as exc:  # noqa: BLE001 - retrieval still works without it
        logger.warning("reranker unavailable (%s); falling back to fused ranking", exc)
        return None
