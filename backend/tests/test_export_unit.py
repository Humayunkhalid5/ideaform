"""Phase 5 export pieces without a database: diagram parsing/drawing, Markdown blocks."""

from __future__ import annotations

from app.schemas.blueprint import ApiResult, ArchitectureResult, RoadmapResult, SchemaResult
from app.services.blueprint import render
from app.services.export import diagrams
from app.services.export.bundle import shift_headings
from app.services.export.mdblocks import parse, plain
from tests.blueprint_fakes import FakeBlueprintProvider

FAKE = FakeBlueprintProvider()


def test_every_generated_diagram_is_drawn():
    arch = render.architecture_diagram(ArchitectureResult.model_validate(FAKE._ArchitectureResult()))
    er = render.er_diagram(SchemaResult.model_validate(FAKE._SchemaResult()))
    flow = render.flow_diagram("Book", ["Search tutors", "Pick a slot", "Pay"])
    road = render.roadmap_diagram(RoadmapResult.model_validate(FAKE._RoadmapResult()))

    chart = diagrams.parse(arch)
    assert isinstance(chart, diagrams.Flowchart) and chart.direction == "LR"
    assert chart.nodes["db"] == ("Database", "store") and chart.nodes["mail"][1] == "external"
    assert ("web", "api", "HTTPS JSON") in chart.edges

    model = diagrams.parse(er)
    assert isinstance(model, diagrams.ErDiagram)
    assert "uuid id PK" in model.entities["USERS"]
    assert model.relations[0][:3] == ("USERS", "1", "BOOKINGS")

    for code in (arch, er, flow, road):
        drawing = diagrams.drawing_for(code)
        assert drawing is not None and 0 < drawing.width <= 492 and drawing.height > 0


def test_unknown_mermaid_falls_back_to_source():
    assert diagrams.drawing_for("sequenceDiagram\n  A->>B: hi") is None
    assert diagrams.drawing_for("flowchart LR\n  this is not valid") is None
    assert diagrams.drawing_for("") is None


def test_png_rendering_for_word():
    png = diagrams.png_for(render.flow_diagram("x", ["One", "Two"]))
    assert png is not None and png[:8] == b"\x89PNG\r\n\x1a\n"


def test_markdown_blocks_cover_the_generated_documents():
    md = render.render_api(ApiResult.model_validate(FAKE._ApiResult()), [], ["note"])
    blocks = parse(md)
    kinds = {b.kind for b in blocks}
    assert {"heading", "paragraph", "table", "list"} <= kinds
    table = next(b for b in blocks if b.kind == "table")
    assert [plain(c) for c in table.header] == ["Method", "Path", "Purpose", "Auth"]
    assert all(len(r) == 4 for r in table.rows)
    # raw HTML is never passed through as markup: it arrives as plain text, escaped by the writers
    html = parse("<script>alert(1)</script>\n\nText")
    assert [b.kind for b in html] == ["paragraph", "paragraph"]
    assert plain(html[0].runs) == "<script>alert(1)</script>"


def test_shift_headings_skips_code_fences():
    text = "# Title\n\n```\n# not a heading\n```\n\n### Sub"
    shifted = shift_headings(text)
    assert shifted.splitlines()[0] == "## Title"
    assert "# not a heading" in shifted and "#### Sub" in shifted


def test_generate_json_repairs_invalid_output_once():
    """Regression: the repair prompt used an unbound exception name (UnboundLocalError)."""
    import pytest

    from app.schemas.nlp import IdeaClassification
    from app.services.llm import ChatMessage, generate_json
    from app.services.llm.base import LLMError, LLMResult, LLMTier

    class Flaky:
        name = "flaky"
        fast_model = strong_model = "m"

        def __init__(self, replies):
            self.replies, self.prompts = list(replies), []

        def complete(self, messages, **kw):
            self.prompts.append(messages)
            return LLMResult(text=self.replies.pop(0), model="m", tokens_in=5, tokens_out=5)

    good = '{"category": "software", "confidence": "high", "rationale": "an app"}'
    provider = Flaky(['{"category": "spaceship"}', good])
    parsed, _ = generate_json(provider, [ChatMessage.user("IDEA: x")], IdeaClassification, tier=LLMTier.FAST)
    assert parsed.category == "software" and len(provider.prompts) == 2
    assert "rejected by the validator" in provider.prompts[1][-1].content  # the error was passed back

    with pytest.raises(LLMError):
        generate_json(Flaky(["not json", "still not json"]), [ChatMessage.user("x")], IdeaClassification)
