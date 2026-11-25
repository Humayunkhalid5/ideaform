"""Provider construction (a single hosted Groq implementation today)."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.groq import GroqProvider


@lru_cache
def get_llm() -> LLMProvider:
    return GroqProvider(get_settings())
