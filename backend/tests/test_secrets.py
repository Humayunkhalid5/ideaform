"""Credential hygiene (plan task 2.8f): keys live in .env only.

Scans every file git tracks (plus untracked, not-ignored files) for Groq/Tavily
key patterns and checks .env is ignored and never served by the API.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
KEY_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),  # Groq
    re.compile(r"tvly-[A-Za-z0-9_-]{20,}"),  # Tavily
]
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".ico", ".woff", ".woff2", ".lock"}


def _repo_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git not available")
    return [REPO / line for line in out.splitlines() if line.strip()]


def test_no_api_keys_in_repository_files():
    offenders = []
    for path in _repo_files():
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(p.search(text) for p in KEY_PATTERNS):
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, f"API keys found in: {offenders}"


def test_env_file_is_git_ignored():
    result = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=REPO)
    assert result.returncode == 0, ".env must be listed in .gitignore"


def test_frontend_only_exposes_the_api_url():
    """Only NEXT_PUBLIC_* variables reach the browser; none may be a secret."""
    names = set()
    for path in (REPO / "frontend").rglob("*.ts*"):
        if "node_modules" in path.parts or ".next" in path.parts:
            continue
        names |= set(re.findall(r"NEXT_PUBLIC_[A-Z_]+", path.read_text(encoding="utf-8", errors="ignore")))
    assert names <= {"NEXT_PUBLIC_API_URL"}, names


def test_health_never_returns_keys(client):
    body = client.get("/health/ready").text + client.get("/health").text
    assert not any(p.search(body) for p in KEY_PATTERNS)
