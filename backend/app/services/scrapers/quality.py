"""Quality filter for fetched pages (AI_DESIGN 3.6)."""

from __future__ import annotations

from app.services.knowledge.text import is_english, word_count, words


def check_quality(
    text: str,
    *,
    raw_size: int,
    min_words: int,
    topic_terms: list[str] | None = None,
) -> str | None:
    """Return a rejection reason, or None when the page is usable."""
    n = word_count(text)
    if n < min_words:
        return f"too short ({n} words)"
    if not is_english(text):
        return "not English"
    # extracted text that is a tiny fraction of a big page is usually a shell/app page
    if raw_size > 200_000 and len(text) / raw_size < 0.01:
        return "mostly boilerplate"
    if topic_terms:
        vocab = set(words(text))
        if not any(term in vocab for term in topic_terms):
            return "off-topic (no idea keywords)"
    return None
