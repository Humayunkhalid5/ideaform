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
) -> tuple[SchemaT, LLMResult]:
    """Return validated output plus the winning call, repairing once on failure."""
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
        logger.info("structured output invalid, attempting one repair: %s", first_error)

    repair = prompt + [
        ChatMessage.assistant(result.text),
        ChatMessage.user(
            f"That output was rejected by the validator:\n{first_error}\n"
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
