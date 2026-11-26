"""Phase 4 blueprint logic without a database: schemas, rendering, diagrams, checks, prompts."""

from __future__ import annotations

import re

from app.schemas.blueprint import ApiResult, ArchitectureResult, ProductDesignResult, SchemaResult
from app.services.blueprint import generators, render
from app.services.blueprint.generators import Context, Upstream, Usage, generate_section
from tests.blueprint_fakes import FakeBlueprintProvider

REFS = [{"id": "R1", "title": "FastAPI docs", "url": "https://fastapi.tiangolo.com", "content": "FastAPI is typed."}]


def ctx(**kw):
    base = dict(title="Tutor finder", idea=generators.idea_block(
        "Tutor finder", "software", "Find tutors.", {"problem": "No trusted tutors"},
        [{"req_type": "functional", "priority": "must", "description": "Search tutors", "confirmed": True}],
    ), evaluation="Overall score: 60/100", references=REFS)
    base.update(kw)
    return Context(**base)


def run_all(provider, context=None):
    context = context or ctx()
    upstream: dict[str, Upstream] = {}
    sections = {}
    for t in generators.ORDER:
        s = generate_section(provider, t, context, upstream, Usage())
        sections[t] = s
        upstream[t] = Upstream(t, 1, {**s.data, "based_on": s.based_on}, s.markdown, False)
    return sections


def mermaid_blocks(markdown: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)\n```", markdown, flags=re.S)


def test_lenient_schemas_normalise_model_drift():
    d = ProductDesignResult.model_validate(FakeBlueprintProvider()._ProductDesignResult())
    assert [r.priority for r in d.requirements] == ["must", "should"]
    assert d.requirements[1].kind == "non_functional" and d.accessibility == ["Keyboard navigation"]
    a = ArchitectureResult.model_validate(FakeBlueprintProvider()._ArchitectureResult())
    assert [c.kind for c in a.components] == ["frontend", "backend", "database", "external"]
    assert a.stack[1].alternatives == ["MySQL"]
    s = SchemaResult.model_validate(FakeBlueprintProvider()._SchemaResult())
    assert s.entities[0].fields[0].pk is True and s.relationships[0].cardinality == "one_to_many"
    api = ApiResult.model_validate(FakeBlueprintProvider()._ApiResult())
    assert api.endpoints[0].method == "POST" and api.endpoints[0].path == "/auth/login"
    assert api.endpoints[1].auth_required is True


def test_architecture_diagram_is_sanitised_and_drops_unknown_links():
    a = ArchitectureResult.model_validate(FakeBlueprintProvider()._ArchitectureResult())
    code = render.architecture_diagram(a)
    assert code.startswith("flowchart LR")
    assert 'db[("Database")]' in code and 'mail(["Email service"])' in code
    assert 'api["API core"]' in code  # quotes stripped from labels
    assert "web -->|\"HTTPS JSON\"| api" in code  # pipe stripped from the edge label
    assert "ghost" not in code


def test_er_diagram_uses_valid_types_keys_and_known_relationships():
    s = SchemaResult.model_validate(FakeBlueprintProvider()._SchemaResult())
    code = render.er_diagram(s)
    assert code.startswith("erDiagram")
    assert "uuid id PK" in code and "varchar email" in code and "uuid user_id FK" in code
    assert 'USERS ||--o{ BOOKINGS : "makes"' in code
    assert "GHOSTS" not in code


def test_review_checks_flag_real_weaknesses():
    s = SchemaResult.model_validate(FakeBlueprintProvider()._SchemaResult())
    notes = render.review_schema(s)
    assert any("`reviews` has no primary key" in n for n in notes)
    assert any("`tutors`" in n for n in notes)  # FK to a missing table
    assert any("`ghosts`" in n for n in notes)
    api = ApiResult.model_validate(FakeBlueprintProvider()._ApiResult())
    api_notes = render.review_api(api)
    assert any("Duplicate endpoint POST /bookings" in n for n in api_notes)
    assert any("DELETE /bookings/{id} changes data without authentication" in n for n in api_notes)
    assert not any("/auth/login" in n for n in api_notes)  # public login is fine
    a = ArchitectureResult.model_validate({"components": [{"id": "api", "name": "API", "kind": "backend"}]})
    arch_notes = render.review_architecture(a)
    assert any("database" in n for n in arch_notes) and any("authentication" in n for n in arch_notes)


def test_full_blueprint_renders_every_section_with_valid_structure():
    provider = FakeBlueprintProvider()
    sections = run_all(provider)
    assert provider.calls == ["ProductDesignResult", "ArchitectureResult", "SchemaResult",
                              "ApiResult", "PrdResult", "RoadmapResult"]
    md = {t: s.markdown for t, s in sections.items()}
    assert md["ui_ux"].startswith("# UI/UX concepts") and len(mermaid_blocks(md["ui_ux"])) == 1
    assert mermaid_blocks(md["architecture"])[0].startswith("flowchart LR")
    assert mermaid_blocks(md["database_schema"])[0].startswith("erDiagram")
    assert "| `POST` | `/bookings` |" in md["api_spec"]
    assert "## Functional requirements" in md["prd"] and "Students search tutors by subject" in md["prd"]
    assert "## Non-functional requirements" in md["prd"] and "Pages load in under 2 seconds" in md["prd"]
    assert "rough estimates" in md["roadmap"] and mermaid_blocks(md["roadmap"])
    # every section records what it was built on
    assert sections["ui_ux"].based_on == {}
    assert sections["roadmap"].based_on == {t: 1 for t in generators.DEPENDENCIES["roadmap"]}
    # review notes appear in the document
    assert "Review notes (automatic checks)" in md["database_schema"]


def test_unknown_references_are_removed_and_used_ones_listed():
    sections = run_all(FakeBlueprintProvider())
    arch = sections["architecture"]
    assert arch.data["result"]["stack"][0]["reference_ids"] == ["R1"]
    assert "[R9]" not in arch.markdown and "[R1]" in arch.markdown
    assert "## References (KB-B)" in arch.markdown and "fastapi.tiangolo.com" in arch.markdown
    assert arch.data["references"] == [{"id": "R1", "title": "FastAPI docs", "url": "https://fastapi.tiangolo.com"}]


def test_prompts_carry_inputs_dependencies_and_instructions():
    provider = FakeBlueprintProvider()
    context = ctx()
    up = {}
    for t in ("ui_ux", "architecture"):
        s = generate_section(provider, t, context, up, Usage())
        up[t] = Upstream(t, 1, s.data, s.markdown, False)
    generate_section(provider, "database_schema", context, up, Usage(), instructions="Use soft deletes.")
    prompt = provider.prompts["SchemaResult"]
    assert "[confirmed] Search tutors" in prompt
    assert "UI UX:" in prompt and "ARCHITECTURE:" in prompt and "REFERENCES:" in prompt
    assert "Use soft deletes." in prompt and "USER INSTRUCTIONS" in prompt
    assert "EVALUATION" not in prompt  # the schema does not use the scores
    assert "EVALUATION" in provider.prompts["ProductDesignResult"]


def test_user_edited_upstream_is_passed_as_text():
    provider = FakeBlueprintProvider()
    edited = Upstream("ui_ux", 2, {"result": {}}, "# UI/UX concepts\nOnly a mobile app with three screens.", True)
    generate_section(provider, "architecture", ctx(), {"ui_ux": edited}, Usage())
    assert "UI UX (edited by the user):" in provider.prompts["ArchitectureResult"]
    assert "Only a mobile app with three screens." in provider.prompts["ArchitectureResult"]


def test_no_references_is_stated_in_the_prompt():
    provider = FakeBlueprintProvider()
    generate_section(provider, "architecture", ctx(references=[]), {}, Usage())
    assert "no technical references were retrieved" in provider.prompts["ArchitectureResult"]
