"""Provider-agnostic LLM interface.

The hosted Groq API implements ``LLMProvider``, so agents never touch HTTP,
headers, or credentials directly.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

Role = Literal["system", "user", "assistant"]


class LLMTier(str, enum.Enum):
    """FAST for classification and extraction, STRONG for evaluation and generation."""

    FAST = "fast"
    STRONG = "strong"


class ChatMessage(BaseModel):
    role: Role
    content: str

    @classmethod
    def system(cls, content: str) -> "ChatMessage":
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> "ChatMessage":
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str) -> "ChatMessage":
        return cls(role="assistant", content=content)


@dataclass
class LLMResult:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0


class LLMError(RuntimeError):
    """Raised when a provider call fails or returns an unusable response."""


class LLMNotConfigured(LLMError):
    """Raised when the provider has no API key."""


class LLMValidationError(LLMError):
    """Raised when model output cannot be parsed into the requested schema."""


class LLMProvider(ABC):
    """Minimal chat-completion surface used across the application."""

    name: str
    fast_model: str
    strong_model: str

    def model_for(self, tier: LLMTier) -> str:
        return self.fast_model if tier == LLMTier.FAST else self.strong_model

    @abstractmethod
    def complete(
        self,
        messages: list[ChatMessage],
        *,
        tier: LLMTier = LLMTier.STRONG,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> LLMResult:
        """Return one completion. Raises ``LLMError`` on failure."""

    @abstractmethod
    def health(self) -> tuple[bool, str]:
        """Cheap reachability probe for the readiness endpoint."""
