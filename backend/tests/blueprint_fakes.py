"""A fake LLM provider for Phase 4 tests: answers by the schema the caller asked for."""

from __future__ import annotations

import json

from app.services.llm.base import LLMProvider, LLMResult

SCHEMAS = ("ProductDesignResult", "ArchitectureResult", "SchemaResult", "ApiResult", "PrdResult", "RoadmapResult")


class FakeBlueprintProvider(LLMProvider):
    """Returns canned JSON per schema and records every prompt it was sent."""

    name = "fake"
    fast_model = "fake-fast"
    strong_model = "fake-strong"

    def __init__(self, *, fail_on: str | None = None):
        self.fail_on = fail_on
        self.calls: list[str] = []
        self.prompts: dict[str, str] = {}  # schema -> last user message

    def health(self):
        return True, "ok"

    def complete(self, messages, *, tier=None, temperature=None, max_tokens=None,
                 json_mode=False, reasoning_effort=None) -> LLMResult:
        schema = messages[-1].content
        name = next((n for n in SCHEMAS if f'"title":"{n}"' in schema), "unknown")
        self.calls.append(name)
        self.prompts[name] = messages[1].content
        if name == self.fail_on:
            from app.services.llm.base import LLMError

            raise LLMError("model unavailable")
        body = getattr(self, f"_{name}", lambda: {})()
        return LLMResult(text=json.dumps(body), model="fake-strong", tokens_in=40, tokens_out=60)

    def _ProductDesignResult(self):
        return {
            "summary": "Students find and book vetted tutors.",
            "requirements": [
                {"text": "Students search tutors by subject", "kind": "functional", "priority": "Must"},
                {"text": "Pages load in under 2 seconds", "kind": "Non-functional", "priority": "should"},
            ],
            "user_roles": [{"name": "Student", "goals": "Find a tutor"}],
            "user_flows": [{"name": "Book a session", "actor": "Student",
                            "steps": ["Search tutors", "Open a profile", "Pick a slot", "Pay"]}],
            "screens": [{"name": "Search", "route": "/search", "purpose": "Find tutors",
                         "key_elements": ["Filters", "Results"]}],
            "design_principles": ["Clarity first"],
            "accessibility": "Keyboard navigation",
        }

    def _ArchitectureResult(self):
        return {
            "summary": "A web app with an API and a database.",
            "stack": [
                {"layer": "Backend", "choice": "FastAPI", "reason": "Typed Python API [R1] [R9]",
                 "alternatives": ["Django"], "reference_ids": ["R1", "R9"]},
                {"layer": "Database", "choice": "PostgreSQL", "reason": "Relational data", "alternatives": "MySQL"},
            ],
            "components": [
                {"id": "web", "name": "Web app", "kind": "UI", "responsibility": "Screens"},
                {"id": "api", "name": "API \"core\"", "kind": "server", "responsibility": "Business logic"},
                {"id": "db", "name": "Database", "kind": "db", "responsibility": "Stores data"},
                {"id": "mail", "name": "Email service", "kind": "third party", "responsibility": "Notifications"},
            ],
            "connections": [
                {"source": "web", "target": "api", "label": "HTTPS | JSON"},
                {"source": "api", "target": "db", "label": "SQL"},
                {"source": "api", "target": "ghost", "label": "dropped"},
            ],
            "data_flow": ["Student searches", "API queries the database"],
            "deployment": ["Containers on one VM"],
            "security": ["JWT authentication on every endpoint", "Validate input"],
            "scalability": ["Cache search results"],
        }

    def _SchemaResult(self):
        return {
            "summary": "Users, tutors and bookings.",
            "entities": [
                {"name": "users", "fields": [
                    {"name": "id", "type": "uuid", "pk": "true"},
                    {"name": "email", "type": "varchar(255)", "nullable": False},
                ]},
                {"name": "bookings", "fields": [
                    {"name": "id", "type": "uuid", "pk": True},
                    {"name": "user_id", "type": "uuid", "fk": "users"},
                    {"name": "tutor_id", "type": "uuid", "fk": "tutors"},
                ]},
                {"name": "reviews", "fields": [{"name": "text", "type": "text"}]},
            ],
            "relationships": [
                {"source": "users", "target": "bookings", "cardinality": "1:N", "label": "makes"},
                {"source": "users", "target": "ghosts", "cardinality": "1:1", "label": "x"},
            ],
            "indexes": ["bookings(user_id)"],
            "notes": ["Users own their bookings"],
        }

    def _ApiResult(self):
        return {
            "summary": "REST API.",
            "base_path": "/api/v1",
            "authentication": "Bearer JWT",
            "endpoints": [
                {"group": "Auth", "method": "post", "path": "auth/login", "summary": "Log in", "auth_required": False},
                {"group": "Bookings", "method": "POST", "path": "/bookings", "summary": "Book", "auth_required": "yes"},
                {"group": "Bookings", "method": "DELETE", "path": "/bookings/{id}", "summary": "Cancel",
                 "auth_required": False},
                {"group": "Bookings", "method": "POST", "path": "/bookings", "summary": "Dup"},
            ],
            "error_format": '{"detail": "..."}',
            "conventions": ["Cursor pagination"],
        }

    def _PrdResult(self):
        return {
            "overview": "A tutoring marketplace.",
            "problem": "Students cannot find trusted tutors.",
            "goals": ["100 bookings in the first month (target)"],
            "target_users": [{"name": "Student", "needs": ["Affordable help"]}],
            "features": [{"name": "Search", "description": "Find tutors", "priority": "MUST"}],
            "success_metrics": "Weekly bookings",
            "risks": ["Low tutor supply"],
        }

    def _RoadmapResult(self):
        return {
            "summary": "Three phases.",
            "phases": [
                {"name": "Setup", "goal": "Repo and CI", "duration": "1 week",
                 "tasks": [{"title": "Create repo", "effort": "1 day"}], "deliverables": ["CI pipeline"]},
                {"name": "MVP", "goal": "Search and booking", "duration": "4 weeks",
                 "tasks": [{"title": "Booking API", "effort": "5 days", "depends_on": "Create repo"}]},
            ],
            "milestones": ["MVP live"],
        }
