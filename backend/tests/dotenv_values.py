"""Read TEST_DATABASE_URL from the environment or from the repo/backend .env files."""

from __future__ import annotations

import os
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]


def load_test_database_url() -> str | None:
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    for env_file in (_BACKEND / ".env", _BACKEND.parent / ".env"):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "TEST_DATABASE_URL" and value.strip():
                return value.strip().strip('"').strip("'")
    return None
