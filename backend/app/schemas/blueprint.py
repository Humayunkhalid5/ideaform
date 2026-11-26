"""Phase 4 blueprint schemas.

LLM-facing models are deliberately lenient (string-or-list, loose casing, missing
fields default) so a slightly-off answer is normalised instead of failing; the API
models are strict.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, field_validator

from app.schemas.evaluation import _text_list

BLUEPRINT_TYPES = ("ui_ux", "architecture", "database_schema", "api_spec", "prd", "roadmap")
BlueprintType = Literal["ui_ux", "architecture", "database_schema", "api_spec", "prd", "roadmap"]

ARTIFACT_TITLES = {
    "prd": "Product requirements (PRD)",
    "architecture": "Architecture",
    "database_schema": "Database schema",
    "api_spec": "API specification",
    "ui_ux": "UI/UX concepts",
    "roadmap": "Development roadmap",
}

TextList = Annotated[list[str], BeforeValidator(_text_list)]
_REF = re.compile(r"R\d{1,2}", re.IGNORECASE)


def _ref_ids(value: object) -> list[str]:
    """Accept ["R1", "[R2]", 3] or "R1, R2" and return ["R1", "R2", "R3"]."""
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    out: list[str] = []
    for item in items:
        found = [f"R{item}"] if isinstance(item, int) else [m.upper() for m in _REF.findall(str(item))]
        out += [r for r in found if r not in out]
    return out


def _lower(value: object) -> object:
    return value.strip().lower().replace(" ", "_").replace("-", "_") if isinstance(value, str) else value


def _bool(value: object) -> object:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "y", "1", "required")
    return value


RefList = Annotated[list[str], BeforeValidator(_ref_ids)]
Priority = Annotated[Literal["must", "should", "could"], BeforeValidator(
    lambda v: (_lower(v) if _lower(v) in ("must", "should", "could") else "should")
)]
Flag = Annotated[bool, BeforeValidator(_bool)]

# ------------------------------------------------------------------ Product Design Agent (ui_ux)


class Requirement(BaseModel):
    text: str
    kind: Literal["functional", "non_functional"] = "functional"
    priority: Priority = "should"

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, v: object) -> object:
        v = _lower(v)
        return "non_functional" if isinstance(v, str) and v.startswith("non") else "functional"


class UserRole(BaseModel):
    name: str
    goals: TextList = Field(default_factory=list)


class UserFlow(BaseModel):
    name: str
    actor: str = "User"
    steps: TextList = Field(default_factory=list)


class Screen(BaseModel):
    name: str
    purpose: str = ""
    key_elements: TextList = Field(default_factory=list)
    route: str | None = None


class ProductDesignResult(BaseModel):
    summary: str = ""
    requirements: list[Requirement] = Field(default_factory=list)
    user_roles: list[UserRole] = Field(default_factory=list)
    user_flows: list[UserFlow] = Field(default_factory=list)
    screens: list[Screen] = Field(default_factory=list)
    design_principles: TextList = Field(default_factory=list)
    accessibility: TextList = Field(default_factory=list)


# ------------------------------------------------------------------ Technical Architect Agent

ComponentKind = Literal[
    "frontend", "backend", "service", "worker", "database", "cache", "queue", "storage", "ai", "external"
]
_KINDS = set(ComponentKind.__args__)  # type: ignore[attr-defined]


class StackChoice(BaseModel):
    layer: str
    choice: str
    reason: str = ""
    alternatives: TextList = Field(default_factory=list)
    reference_ids: RefList = Field(default_factory=list)


class Component(BaseModel):
    id: str
    name: str
    kind: ComponentKind = "service"
    responsibility: str = ""

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, v: object) -> object:
        v = _lower(v)
        aliases = {"db": "database", "ui": "frontend", "client": "frontend", "api": "backend",
                   "server": "backend", "llm": "ai", "ml": "ai", "third_party": "external",
                   "message_queue": "queue", "broker": "queue", "object_storage": "storage"}
        v = aliases.get(v, v) if isinstance(v, str) else v
        return v if v in _KINDS else "service"


class Connection(BaseModel):
    source: str
    target: str
    label: str = ""


class ArchitectureResult(BaseModel):
    summary: str = ""
    stack: list[StackChoice] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    data_flow: TextList = Field(default_factory=list)
    deployment: TextList = Field(default_factory=list)
    security: TextList = Field(default_factory=list)
    scalability: TextList = Field(default_factory=list)


# ------------------------------------------------------------------ database schema generator


class Field_(BaseModel):
    name: str
    type: str = "text"
    pk: Flag = False
    fk: str | None = None  # referenced entity name
    nullable: Flag = True
    note: str = ""


class Entity(BaseModel):
    name: str
    description: str = ""
    fields: list[Field_] = Field(default_factory=list)


class Relationship(BaseModel):
    source: str
    target: str
    cardinality: Literal["one_to_one", "one_to_many", "many_to_many"] = "one_to_many"
    label: str = "has"

    @field_validator("cardinality", mode="before")
    @classmethod
    def _card(cls, v: object) -> object:
        v = _lower(v)
        if isinstance(v, str):
            if "many_to_many" in v or v in ("n:m", "m:n", "*:*"):
                return "many_to_many"
            if "one_to_one" in v or v == "1:1":
                return "one_to_one"
        return "one_to_many"


class SchemaResult(BaseModel):
    summary: str = ""
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    indexes: TextList = Field(default_factory=list)
    notes: TextList = Field(default_factory=list)


# ------------------------------------------------------------------ API specification generator

_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


class Endpoint(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    path: str
    summary: str = ""
    auth_required: Flag = True
    request: str = ""
    response: str = ""
    status_codes: TextList = Field(default_factory=list)
    group: str = "General"

    @field_validator("method", mode="before")
    @classmethod
    def _method(cls, v: object) -> object:
        v = str(v or "GET").strip().upper()
        return v if v in _METHODS else "GET"

    @field_validator("path", mode="before")
    @classmethod
    def _path(cls, v: object) -> object:
        v = str(v or "/").strip()
        return v if v.startswith("/") else "/" + v


class ApiResult(BaseModel):
    summary: str = ""
    base_path: str = "/api"
    authentication: str = ""
    endpoints: list[Endpoint] = Field(default_factory=list)
    error_format: str = ""
    conventions: TextList = Field(default_factory=list)


# ------------------------------------------------------------------ documentation generators


class Persona(BaseModel):
    name: str
    needs: TextList = Field(default_factory=list)


class Feature(BaseModel):
    name: str
    description: str = ""
    priority: Priority = "should"


class PrdResult(BaseModel):
    overview: str = ""
    problem: str = ""
    goals: TextList = Field(default_factory=list)
    non_goals: TextList = Field(default_factory=list)
    target_users: list[Persona] = Field(default_factory=list)
    scope_in: TextList = Field(default_factory=list)
    scope_out: TextList = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    success_metrics: TextList = Field(default_factory=list)
    assumptions: TextList = Field(default_factory=list)
    risks: TextList = Field(default_factory=list)
    open_questions: TextList = Field(default_factory=list)


class Task(BaseModel):
    title: str
    effort: str = ""
    depends_on: TextList = Field(default_factory=list)


class Phase(BaseModel):
    name: str
    goal: str = ""
    duration: str = ""
    tasks: list[Task] = Field(default_factory=list)
    deliverables: TextList = Field(default_factory=list)


class RoadmapResult(BaseModel):
    summary: str = ""
    phases: list[Phase] = Field(default_factory=list)
    milestones: TextList = Field(default_factory=list)
    assumptions: TextList = Field(default_factory=list)


RESULT_SCHEMAS: dict[str, type[BaseModel]] = {
    "ui_ux": ProductDesignResult,
    "architecture": ArchitectureResult,
    "database_schema": SchemaResult,
    "api_spec": ApiResult,
    "prd": PrdResult,
    "roadmap": RoadmapResult,
}

# ------------------------------------------------------------------ API models


class ArtifactOut(BaseModel):
    id: uuid.UUID
    artifact_type: str
    title: str
    format: str
    content: str
    data: dict | None = None
    artifact_version: int
    edited_by_user: bool
    instructions: str | None = None
    run_id: uuid.UUID | None = None
    created_at: datetime
    # sections this one was built from that have changed since (type -> newer version)
    stale_inputs: list[str] = Field(default_factory=list)


class BlueprintOut(BaseModel):
    project_id: uuid.UUID
    version_no: int
    artifacts: list[ArtifactOut]
    missing: list[str]
    has_evaluation: bool


class RegenerateRequest(BaseModel):
    instructions: str | None = Field(default=None, max_length=2_000)


class ArtifactEdit(BaseModel):
    content: str = Field(min_length=1, max_length=200_000)
