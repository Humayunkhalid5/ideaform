"""Word (.docx) export with python-docx: same content as the PDF, diagrams as PNG images."""

from __future__ import annotations

import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.services.export import diagrams
from app.services.export.bundle import DISCLAIMER, MISSING_TITLES, ExportBundle
from app.services.export.mdblocks import Block, Run, parse

NAVY = RGBColor(0x14, 0x21, 0x3D)
MUTED = RGBColor(0x64, 0x74, 0x8B)
PRIMARY = RGBColor(0x4F, 0x46, 0xE5)


def _hyperlink(paragraph, url: str, text: str, bold: bool, italic: bool) -> None:
    part = paragraph.part
    rel = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rel)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "4F46E5")
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    props.append(color)
    props.append(underline)
    if bold:
        props.append(OxmlElement("w:b"))
    if italic:
        props.append(OxmlElement("w:i"))
    run.append(props)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    run.append(t)
    link.append(run)
    paragraph._p.append(link)


def _runs(paragraph, runs: list[Run]) -> None:
    for r in runs:
        if r.href and r.href.startswith(("http://", "https://")):
            _hyperlink(paragraph, r.href, r.text, r.bold, r.italic)
            continue
        run = paragraph.add_run(r.text)
        run.bold, run.italic = r.bold or None, r.italic or None
        if r.code:
            run.font.name = "Consolas"
            run.font.size = Pt(9)


def _blocks(doc, blocks: list[Block], *, list_level: int = 0) -> None:
    for b in blocks:
        if b.kind == "heading":
            _runs(doc.add_heading(level=min(4, b.level + 1)), b.runs)
        elif b.kind == "paragraph":
            _runs(doc.add_paragraph(), b.runs)
        elif b.kind == "list":
            style = "List Number" if b.ordered else "List Bullet"
            if list_level:
                style += f" {min(3, list_level + 1)}"
            for item in b.items:
                first, rest = (item[0], item[1:]) if item and item[0].kind == "paragraph" else (None, item)
                p = doc.add_paragraph(style=style)
                if first is not None:
                    _runs(p, first.runs)
                _blocks(doc, rest, list_level=list_level + 1)
        elif b.kind == "table":
            ncols = max([len(b.header)] + [len(r) for r in b.rows]) or 1
            table = doc.add_table(rows=0, cols=ncols)
            table.style = "Table Grid"
            for i, row in enumerate(([b.header] if b.header else []) + b.rows):
                cells = table.add_row().cells
                for j, cell in enumerate(row[:ncols]):
                    p = cells[j].paragraphs[0]
                    _runs(p, cell)
                    for run in p.runs:
                        run.font.size = Pt(8.5)
                        if i == 0 and b.header:
                            run.bold = True
            doc.add_paragraph()
        elif b.kind == "code":
            png = diagrams.png_for(b.text) if b.lang == "mermaid" else None
            if png:
                doc.add_picture(io.BytesIO(png), width=Inches(6.0))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p = doc.add_paragraph()
                run = p.add_run(b.text)
                run.font.name = "Consolas"
                run.font.size = Pt(8)
        elif b.kind == "quote":
            for child in b.children:
                if child.kind == "paragraph":
                    p = doc.add_paragraph(style="Intense Quote")
                    _runs(p, child.runs)
                else:
                    _blocks(doc, [child])
        elif b.kind == "hr":
            doc.add_paragraph("―" * 20).alignment = WD_ALIGN_PARAGRAPH.CENTER


def to_docx(bundle: ExportBundle) -> bytes:
    doc = Document()
    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10.5)
    for level in range(1, 5):
        styles[f"Heading {level}"].font.color.rgb = NAVY
    props = doc.core_properties
    props.title = f"{bundle.project.title} · IdeaForm export"
    props.author = "IdeaForm"
    props.subject = f"Version {bundle.version.version_no}"

    doc.add_heading(bundle.project.title, level=0)
    meta = [f"Category: {bundle.project.category}", f"Idea version {bundle.version.version_no}",
            f"Exported {bundle.generated_at:%d %B %Y, %H:%M} UTC"]
    if bundle.overall_score is not None:
        meta.insert(0, f"Overall evaluation score: {bundle.overall_score}/100")
    for line in meta:
        doc.add_paragraph(line)
    note = doc.add_paragraph()
    run = note.add_run(DISCLAIMER)
    run.italic, run.font.color.rgb, run.font.size = True, MUTED, Pt(9)

    doc.add_heading("Contents", level=1)
    for i, s in enumerate(bundle.sections, 1):
        doc.add_paragraph(f"{i}. {s.title}" + (f" ({s.note})" if s.note else ""))
    if bundle.missing:
        doc.add_paragraph("Not generated yet: " + ", ".join(MISSING_TITLES.get(m, m) for m in bundle.missing))

    for s in bundle.sections:
        doc.add_page_break()
        doc.add_heading(s.title, level=1)
        if s.note:
            p = doc.add_paragraph()
            r = p.add_run(s.note)
            r.italic, r.font.color.rgb = True, MUTED
        blocks = parse(s.markdown)
        if blocks and blocks[0].kind == "heading" and blocks[0].level == 1:
            blocks = blocks[1:]
        _blocks(doc, blocks)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
