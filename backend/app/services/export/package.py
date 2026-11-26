"""ZIP package: the report in every format, each section as Markdown, diagrams, and data."""

from __future__ import annotations

import io
import zipfile

from app.services.export.bundle import ExportBundle, mermaid_blocks, to_json, to_markdown
from app.services.export.pdf import to_pdf
from app.services.export.word import to_docx


def to_zip(bundle: ExportBundle) -> bytes:
    buffer = io.BytesIO()
    root = bundle.slug
    manifest = [f"IdeaForm export: {bundle.project.title} (version {bundle.version.version_no})",
                f"Exported {bundle.generated_at:%Y-%m-%d %H:%M} UTC", "", "Contents:"]
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        def add(path: str, data: bytes | str, what: str) -> None:
            z.writestr(f"{root}/{path}", data)
            manifest.append(f"  {path:<44} {what}")

        add("report.pdf", to_pdf(bundle), "Full report (PDF)")
        add("report.docx", to_docx(bundle), "Full report (Word)")
        add("report.md", to_markdown(bundle), "Full report (Markdown)")
        for i, s in enumerate(bundle.sections, 1):
            add(f"sections/{i:02d}-{s.key}.md", s.markdown, s.title + (f" ({s.note})" if s.note else ""))
            for j, code in enumerate(mermaid_blocks(s.markdown), 1):
                add(f"diagrams/{s.key}-{j}.mmd", code + "\n", f"Mermaid source, {s.title}")
        add("data/project.json", to_json(bundle), "Idea, requirements, evaluation, evidence, artifact data")
        if bundle.missing:
            manifest += ["", "Not generated yet: " + ", ".join(bundle.missing)]
        z.writestr(f"{root}/README.txt", "\n".join(manifest) + "\n")
    return buffer.getvalue()
