"""Hosted Groq provider (OpenAI-compatible chat completions).

The API key comes from settings, which reads it from ``.env``; it is never
logged, never echoed in errors, and never returned to a client.
"""

from __future__ import annotations

import logging
import random
import re
import time

import httpx

from app.config import Settings
from app.services.llm.base import (
    ChatMessage,
    LLMError,
    LLMNotConfigured,
    LLMProvider,
    LLMResult,
    LLMTier,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
# 429s on the free tier mean "tokens per minute used up"; waiting for the window
# to reset is the only fix, so they get more attempts and honour Retry-After.
MAX_RATE_LIMIT_ATTEMPTS = 6
MAX_RETRY_AFTER_SECONDS = 65.0


def _retry_after(response: httpx.Response) -> float | None:
    """Seconds to wait from ``Retry-After`` or Groq's reset header, if present."""
    for header in ("retry-after", "x-ratelimit-reset-tokens"):
        value = response.headers.get(header)
        if not value:
            continue
        try:
            return min(float(value), MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            pass
        # Groq durations look like "7.66s", "1m26.4s" or "697ms"
        total, matched = 0.0, False
        for amount, unit in re.findall(r"([\d.]+)(ms|s|m|h)", value):
            matched = True
            total += float(amount) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
        if matched:
            return min(total, MAX_RETRY_AFTER_SECONDS)
    return None


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, settings: Settings) -> None:
        self.fast_model = settings.llm_model_fast
        self.strong_model = settings.llm_model_strong
        self._base_url = settings.groq_base_url.rstrip("/")
        self._api_key = settings.groq_api_key
        self._timeout = settings.llm_request_timeout
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise LLMNotConfigured(
                "GROQ_API_KEY is not set. Put it in .env (never in code or in a commit)."
            )
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float | None,
        max_tokens: int | None,
        json_mode: bool,
        reasoning_effort: str | None = None,
    ) -> dict:
        payload: dict = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "temperature": self._temperature if temperature is None else temperature,
            "max_tokens": self._max_tokens if max_tokens is None else max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        # gpt-oss models spend completion tokens on hidden reasoning; "low" keeps
        # long structured outputs inside the free tier's per-minute token budget
        if reasoning_effort and "gpt-oss" in model:
            payload["reasoning_effort"] = reasoning_effort
        return payload

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            error = response.json().get("error")
        except (ValueError, AttributeError):
            return response.text[:300]
        if isinstance(error, dict):
            error = error.get("message", error)
        return str(error or response.text)[:300]

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        tier: LLMTier = LLMTier.STRONG,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        reasoning_effort: str | None = None,
    ) -> LLMResult:
        if not messages:
            raise LLMError("At least one message is required.")

        model = self.model_for(tier)
        payload = self._payload(
            messages, model, temperature, max_tokens, json_mode, reasoning_effort
        )
        url = f"{self._base_url}/chat/completions"
        started = time.perf_counter()
        last_error = "unknown error"

        attempt, rate_limited = 0, 0
        while True:
            attempt += 1
            wait: float | None = None
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(url, headers=self._headers(), json=payload)
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("groq transport error (attempt %s/%s)", attempt, MAX_ATTEMPTS)
            else:
                if response.status_code == 200:
                    return self._parse(response, model, started)
                last_error = f"HTTP {response.status_code}: {self._error_detail(response)}"
                if response.status_code not in RETRYABLE_STATUS:
                    raise LLMError(f"Groq request failed ({last_error})")
                if response.status_code == 429:
                    rate_limited += 1
                    wait = _retry_after(response)
                logger.warning(
                    "groq retryable error %s (attempt %s), waiting %s s",
                    response.status_code,
                    attempt,
                    round(wait, 1) if wait is not None else "backoff",
                )

            limit = MAX_RATE_LIMIT_ATTEMPTS if rate_limited else MAX_ATTEMPTS
            if attempt >= limit:
                break
            if wait is None:
                wait = min(2 ** (attempt - 1) + random.random(), 8)
            time.sleep(wait + random.random() * 0.5)

        raise LLMError(f"Groq request failed after {attempt} attempts ({last_error})")

    def _parse(self, response: httpx.Response, model: str, started: float) -> LLMResult:
        try:
            body = response.json()
            choice = body["choices"][0]
            text = (choice["message"].get("content") or "").strip()
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected Groq response shape: {exc}") from exc

        if not text:
            raise LLMError("Groq returned an empty completion.")
        if choice.get("finish_reason") == "length":
            logger.warning("completion truncated at max_tokens=%s", self._max_tokens)

        usage = body.get("usage") or {}
        return LLMResult(
            text=text,
            model=body.get("model", model),
            tokens_in=int(usage.get("prompt_tokens") or 0),
            tokens_out=int(usage.get("completion_tokens") or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def health(self) -> tuple[bool, str]:
        if not self._api_key:
            return False, "GROQ_API_KEY missing"
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self._base_url}/models", headers=self._headers())
        except httpx.HTTPError as exc:
            return False, type(exc).__name__
        return (True, "ok") if response.status_code == 200 else (False, f"HTTP {response.status_code}")
