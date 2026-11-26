"""JSON-validated generation with exactly one repair attempt."""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.services.llm.base import (
    ChatMessage,
    LLMError,
    LLMProvider,
    LLMResult,
    LLMValidationError,
    LLMTier,
)

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _parse(text: str, schema: type[SchemaT]) -> SchemaT:
    """Parse model text as JSON and validate it into ``schema``."""
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        return schema.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMValidationError(f"Output does not match {schema.__name__}: {exc}") from exc


def generate_json(
    provider: LLMProvider,
    messages: list[ChatMessage],
    schema: type[SchemaT],
    *,
    tier: LLMTier = LLMTier.STRONG,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
    cache: bool = False,
) -> tuple[SchemaT, LLMResult]:
    """Return validated output plus the winning call, repairing once on failure.

    With ``cache=True`` an identical earlier request (same provider, model, messages, schema
    and parameters, by SHA-256) is answered from the cache: no model call, zero tokens.
    """
    if not cache:
        return _generate(provider, messages, schema, tier, temperature, max_tokens, reasoning_effort)

    from app.services.llm import cache as llm_cache

    model = getattr(provider, "fast_model" if tier == LLMTier.FAST else "strong_model", None)
    key = llm_cache.cache_key(
        provider=getattr(provider, "name", type(provider).__name__),
        model=model,
        messages=[(m.role, m.content) for m in messages],
        schema=schema.model_json_schema(),
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    )
    hit = llm_cache.lookup(key)
    if hit is not None:
        try:
            parsed = _parse(hit.text, schema)
            logger.info("llm cache hit for %s", schema.__name__)
            return parsed, LLMResult(text=hit.text, model=hit.model, tokens_in=0, tokens_out=0)
        except LLMValidationError:
            pass  # schema changed since it was cached: ask the model again
    parsed, result = _generate(provider, messages, schema, tier, temperature, max_tokens, reasoning_effort)
    llm_cache.store(key, llm_cache.CachedReply(result.text, result.model, result.tokens_in, result.tokens_out))
    return parsed, result


def _generate(
    provider: LLMProvider,
    messages: list[ChatMessage],
    schema: type[SchemaT],
    tier: LLMTier,
    temperature: float | None,
    max_tokens: int | None,
    reasoning_effort: str | None,
) -> tuple[SchemaT, LLMResult]:
    schema_hint = json.dumps(schema.model_json_schema(), separators=(",", ":"))
    prompt = messages + [
        ChatMessage.system(
            "Reply with a single JSON object and nothing else. "
            f"It must validate against this JSON schema:\n{schema_hint}"
        )
    ]

    extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
    result = provider.complete(
        prompt, tier=tier, temperature=temperature, max_tokens=max_tokens, json_mode=True, **extra
    )
    try:
        return _parse(result.text, schema), result
    except LLMValidationError as first_error:
        # keep the message: Python unbinds ``first_error`` when the except block ends
        problem = str(first_error)
        logger.info("structured output invalid, attempting one repair: %s", problem)

    repair = prompt + [
        ChatMessage.assistant(result.text),
        ChatMessage.user(
            f"That output was rejected by the validator:\n{problem}\n"
            "Return only the corrected JSON object."
        ),
    ]
    retried = provider.complete(
        repair, tier=tier, temperature=0.0, max_tokens=max_tokens, json_mode=True, **extra
    )
    try:
        return _parse(retried.text, schema), retried
    except LLMValidationError as second_error:
        raise LLMError(str(second_error)) from second_error
