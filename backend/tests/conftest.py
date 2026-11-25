"""Test fixtures.

The suite needs a real PostgreSQL database (JSONB, CHECK constraints, generated
tsvector columns). Point ``TEST_DATABASE_URL`` at a *dedicated* database: every
table in it is dropped and recreated. Without it, database tests are skipped.

The LLM is never called: extraction functions are replaced by fakes.
"""

from __future__ import annotations

import os

# Settings are read at import time, so configure the environment first.
os.environ["ENVIRONMENT"] = "test"
os.environ["JOBS_INLINE"] = "true"
os.environ["JWT_SECRET"] = "test-secret-not-for-production"
os.environ["GROQ_API_KEY"] = ""  # never call the real LLM from tests
os.environ["TAVILY_API_KEY"] = ""  # never call the real search API from tests
os.environ["EMBEDDING_BACKEND"] = "hashing"  # no model download in tests
os.environ["RERANKER_ENABLED"] = "false"
os.environ["SCRAPER_MIN_DELAY_SECONDS"] = "0"
os.environ["SCRAPER_PLAYWRIGHT_ENABLED"] = "false"

from tests.dotenv_values import load_test_database_url  # noqa: E402

TEST_DATABASE_URL = load_test_database_url()
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.rate_limit import auth_limiter  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import app  # noqa: E402
from app.schemas.nlp import (  # noqa: E402
    IdeaClassification,
    RequirementItem,
    StructuredIdea,
)
from app.services.llm.base import LLMResult  # noqa: E402

EMBEDDINGS_FALLBACK = (
    "CREATE TABLE IF NOT EXISTS embeddings ("
    " chunk_id UUID PRIMARY KEY REFERENCES research_chunks (id) ON DELETE CASCADE,"
    " model_name TEXT NOT NULL, embedding REAL[] NOT NULL)"
)


@pytest.fixture(scope="session")
def engine():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    eng = create_engine(TEST_DATABASE_URL, future=True)
    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        conn.execute(text("DROP TABLE IF EXISTS embeddings CASCADE"))
        Base.metadata.drop_all(conn)
        tables = [t for name, t in Base.metadata.tables.items() if name != "embeddings"]
        Base.metadata.create_all(conn, tables=tables)
        conn.execute(text(EMBEDDINGS_FALLBACK))
    yield eng
    with eng.begin() as conn:
        Base.metadata.drop_all(conn)
    eng.dispose()


@pytest.fixture
def db_session(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    yield session
    session.close()
    names = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(engine, db_session):
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    auth_limiter.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    auth_limiter.reset()


# ---------------------------------------------------------------- helpers


def register_and_login(client: TestClient, email: str, password: str = "password123") -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register_and_login(client, "alice@example.com")


@pytest.fixture
def other_auth(client):
    return register_and_login(client, "bob@example.com")


IDEA = (
    "An AI platform that helps university students find affordable tutors, "
    "with verified reviews and in-app scheduling."
)


@pytest.fixture
def project(client, auth):
    r = client.post(
        "/projects", json={"title": "Tutor finder", "idea_text": IDEA}, headers=auth
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- fake LLM


TOKENS = 100  # in + out tokens per fake call, 50 each


def _result() -> LLMResult:
    return LLMResult(text="{}", model="fake-model", tokens_in=TOKENS // 2, tokens_out=TOKENS // 2)


class FakeLLM:
    def __init__(self) -> None:
        self.requirements = [
            RequirementItem(req_type="functional", description="Students can search tutors by subject", priority="must"),
            RequirementItem(req_type="functional", description="Students can book a session", priority="must"),
            RequirementItem(req_type="non_functional", description="Search returns results within 2 seconds", priority="should"),
        ]
        self.fail_with: Exception | None = None

    def classify(self, idea_text: str):
        if self.fail_with:
            raise self.fail_with
        return IdeaClassification(category="business", confidence="high", rationale="marketplace"), _result()

    def extract(self, idea_text: str, category: str):
        return (
            StructuredIdea(
                category=category,
                problem="Tutors are expensive and hard to vet",
                target_users=["university students"],
                key_features=["search", "reviews", "scheduling"],
            ),
            _result(),
        )

    def requirements_(self, idea_text: str):
        if self.fail_with:
            raise self.fail_with
        return list(self.requirements), _result()


@pytest.fixture
def fake_llm(monkeypatch):
    from app.services.nlp import pipeline

    fake = FakeLLM()
    monkeypatch.setattr(pipeline, "classify_idea", fake.classify)
    monkeypatch.setattr(pipeline, "extract_idea", fake.extract)
    monkeypatch.setattr(pipeline, "extract_requirements", fake.requirements_)
    return fake
