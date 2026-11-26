"""PDF export with ReportLab: cover, contents, every section, diagrams drawn as vectors."""

from __future__ import annotations

import io
import os
from xml.sax.saxutils import escape

import reportlab
from reportlab.graphics.shapes import Drawing, Line, PolyLine
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.export import diagrams
from app.services.export.bundle import DISCLAIMER, MISSING_TITLES, ExportBundle
from app.services.export.mdblocks import Block, Run, parse, plain

NAVY = colors.HexColor("#14213d")
INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#e2e8f0")
SOFT = colors.HexColor("#f4f6fb")
COPPER = colors.HexColor("#c88a6a")
TEAL = colors.HexColor("#6fa8a3")
PRIMARY = colors.HexColor("#4f46e5")

_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
_REGISTERED = False
_GLYPHS: set[int] = set()
_REPLACE = {"→": "->", "←": "<-", "↔": "<->", "≥": ">=", "≤": "<=", "≈": "~", "✓": "v", "✔": "v",
            "✗": "x", "★": "*", " ": " ", "​": "",
            # dash and space variants models like to emit (non-breaking hyphen, minus, thin spaces)
            "‐": "-", "‑": "-", "‒": "-", "−": "-", "⁃": "-",
            " ": " ", " ": " ", " ": " ", " ": " "}


def _fonts() -> None:
    """Bitstream Vera (shipped with ReportLab) covers Latin text far beyond the base-14 fonts."""
    global _REGISTERED, _GLYPHS
    if _REGISTERED:
        return
    for name, file in (("Vera", "Vera.ttf"), ("Vera-Bold", "VeraBd.ttf"),
                       ("Vera-Italic", "VeraIt.ttf"), ("Vera-BoldItalic", "VeraBI.ttf")):
        pdfmetrics.registerFont(TTFont(name, os.path.join(_FONT_DIR, file)))
    pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="Vera-Bold", italic="Vera-Italic", boldItalic="Vera-BoldItalic")
    _GLYPHS = set(pdfmetrics.getFont("Vera").face.charToGlyph)
    _REGISTERED = True


def clean(text: str) -> str:
    """Replace characters the font cannot draw instead of printing empty boxes."""
    out = []
    for ch in text:
        ch = _REPLACE.get(ch, ch)
        out.append(ch if len(ch) != 1 or ord(ch) < 128 or ord(ch) in _GLYPHS else "?")
    return "".join(out)


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("body", fontName="Vera", fontSize=9.5, leading=14, textColor=INK, alignment=TA_LEFT, spaceAfter=5)
    return {
        "body": base,
        "small": ParagraphStyle("small", parent=base, fontSize=8, leading=11, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8, leading=10.5, spaceAfter=0),
        "cellhead": ParagraphStyle("cellhead", parent=base, fontName="Vera-Bold", fontSize=8, leading=10.5, spaceAfter=0),
        "quote": ParagraphStyle("quote", parent=base, textColor=MUTED, leftIndent=10, fontName="Vera-Italic"),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=7.5, leading=9.5, textColor=INK, backColor=SOFT,
                               borderPadding=6, leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=8),
        "h1": ParagraphStyle("h1", parent=base, fontName="Vera-Bold", fontSize=17, leading=22, textColor=NAVY, spaceBefore=4, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base, fontName="Vera-Bold", fontSize=13, leading=17, textColor=NAVY, spaceBefore=12, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base, fontName="Vera-Bold", fontSize=11, leading=15, textColor=INK, spaceBefore=9, spaceAfter=4),
        "h4": ParagraphStyle("h4", parent=base, fontName="Vera-Bold", fontSize=9.5, leading=13, textColor=INK, spaceBefore=6, spaceAfter=3),
        "title": ParagraphStyle("title", parent=base, fontName="Vera-Bold", fontSize=26, leading=31, textColor=NAVY, spaceAfter=10),
        "toc": ParagraphStyle("toc", parent=base, fontSize=10.5, leading=17),
    }


def _markup(runs: list[Run]) -> str:
    parts = []
    for r in runs:
        text = escape(clean(r.text)).replace("\n", "<br/>")
        if r.code:
            text = f'<font face="Courier" size="8" backColor="#f4f6fb">{text}</font>'
        if r.bold:
            text = f"<b>{text}</b>"
        if r.italic:
            text = f"<i>{text}</i>"
        if r.href and r.href.startswith(("http://", "https://")):
            text = f'<link href="{escape(r.href)}" color="#4f46e5">{text}</link>'
        parts.append(text)
    return "".join(parts) or "&nbsp;"


def _table(block: Block, styles, width: float) -> Table:
    ncols = max([len(block.header)] + [len(r) for r in block.rows]) or 1
    lengths = [0] * ncols
    longest_word = [0] * ncols
    for row in [block.header, *block.rows]:
        for i, cell in enumerate(row):
            text = plain(cell)
            lengths[i] = max(lengths[i], min(len(text), 60))
            longest_word[i] = max([longest_word[i]] + [len(w) for w in text.split()])
    total = sum(max(n, 4) for n in lengths)
    widths = [width * max(n, 4) / total for n in lengths]
    # never narrower than the longest word (so "frontend" is not split), capped at 40% of the table
    floors = [min(width * 0.4, w * 4.9 + 10) for w in longest_word]
    for _ in range(3):
        short = [i for i in range(ncols) if widths[i] < floors[i]]
        if not short:
            break
        need = sum(floors[i] - widths[i] for i in short)
        donors = [i for i in range(ncols) if i not in short and widths[i] > floors[i]]
        spare = sum(widths[i] - floors[i] for i in donors)
        if spare <= 0:
            break
        take = min(need, spare)
        for i in short:
            widths[i] += (floors[i] - widths[i]) * take / need
        for i in donors:
            widths[i] -= (widths[i] - floors[i]) * take / spare
    data = []
    if block.header:
        data.append([Paragraph(_markup(c), styles["cellhead"]) for c in block.header] + [""] * (ncols - len(block.header)))
    for row in block.rows:
        data.append([Paragraph(_markup(c), styles["cell"]) for c in row] + [""] * (ncols - len(row)))
    table = Table(data, colWidths=widths, repeatRows=1 if block.header else 0)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT if block.header else colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
    ]))
    return table


def flowables(blocks: list[Block], styles, width: float, *, base_level: int = 0) -> list:
    out: list = []
    for b in blocks:
        if b.kind == "heading":
            level = min(4, b.level + base_level)
            out.append(CondPageBreak(30 * mm) if level <= 2 else Spacer(0, 0))
            out.append(Paragraph(_markup(b.runs), styles[f"h{level}"]))
        elif b.kind == "paragraph":
            out.append(Paragraph(_markup(b.runs), styles["body"]))
        elif b.kind == "list":
            items = [ListItem(flowables(item, styles, width - 14), leftIndent=12) for item in b.items]
            out.append(ListFlowable(items, bulletType="1" if b.ordered else "bullet", start=None if b.ordered else "•",
                                    bulletFontName="Vera", bulletFontSize=8, leftIndent=12, spaceAfter=4))
        elif b.kind == "table":
            out.append(_table(b, styles, width))
            out.append(Spacer(0, 6))
        elif b.kind == "code":
            drawing = diagrams.drawing_for(b.text) if b.lang == "mermaid" else None
            if drawing is not None:
                out.append(KeepTogether([Spacer(0, 4), drawing, Spacer(0, 8)]))
            else:
                if b.lang == "mermaid":
                    out.append(Paragraph("Diagram source (Mermaid):", styles["small"]))
                out.append(Preformatted(clean(b.text), styles["code"], maxLineLength=110))
        elif b.kind == "quote":
            for child in flowables(b.children, styles, width - 12):
                if isinstance(child, Paragraph):
                    child = Paragraph(child.text, styles["quote"])
                out.append(child)
        elif b.kind == "hr":
            out.append(HRFlowable(width="100%", color=LINE, thickness=0.6, spaceBefore=6, spaceAfter=6))
    return out


def _mark(size: float = 64) -> Drawing:
    """The hexagon-and-bulb mark, simplified for print (copper outline, teal bulb)."""
    d = Drawing(size, size)
    s = size / 100
    hexagon = [50, 95, 91, 72, 91, 26, 50, 4, 9, 26, 9, 72, 50, 95]
    d.add(PolyLine([v * s for v in hexagon], strokeColor=COPPER, strokeWidth=3 * s * 1.2, strokeLineJoin=1))
    bulb = [42, 22, 42, 30, 34, 40, 33, 52, 40, 64, 50, 68, 60, 64, 67, 52, 66, 40, 58, 30, 58, 22]
    d.add(PolyLine([v * s for v in bulb], strokeColor=TEAL, strokeWidth=3 * s * 1.2, strokeLineJoin=1))
    d.add(Line(43 * s, 16 * s, 57 * s, 16 * s, strokeColor=TEAL, strokeWidth=3 * s * 1.2))
    return d


def to_pdf(bundle: ExportBundle) -> bytes:
    _fonts()
    styles = _styles()
    buffer = io.BytesIO()
    margin = 20 * mm
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=22 * mm, bottomMargin=18 * mm,
        title=f"{bundle.project.title} · IdeaForm export", author="IdeaForm",
        subject=f"Version {bundle.version.version_no}", creator="IdeaForm (ReportLab)",
    )
    width = A4[0] - 2 * margin

    def decorate(canvas, document) -> None:
        canvas.saveState()
        if document.page > 1:
            canvas.setFont("Vera", 7.5)
            canvas.setFillColor(MUTED)
            canvas.drawString(margin, A4[1] - 13 * mm, clean(f"{bundle.project.title} · version {bundle.version.version_no}"))
            canvas.drawRightString(A4[0] - margin, A4[1] - 13 * mm, "IdeaForm")
            canvas.setStrokeColor(LINE)
            canvas.line(margin, A4[1] - 15 * mm, A4[0] - margin, A4[1] - 15 * mm)
        canvas.setFont("Vera", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    story: list = [Spacer(0, 30 * mm), _mark(70), Spacer(0, 10 * mm),
                   Paragraph(escape(clean(bundle.project.title)), styles["title"])]
    meta = [
        f"Category: {bundle.project.category}",
        f"Idea version {bundle.version.version_no}",
        f"Exported {bundle.generated_at:%d %B %Y, %H:%M} UTC",
    ]
    if bundle.overall_score is not None:
        meta.insert(0, f"Overall evaluation score: {bundle.overall_score}/100")
    for line in meta:
        story.append(Paragraph(escape(line), styles["body"]))
    story += [Spacer(0, 8 * mm), HRFlowable(width="100%", color=COPPER, thickness=1.2),
              Spacer(0, 4 * mm), Paragraph(escape(DISCLAIMER), styles["small"]), PageBreak(),
              Paragraph("Contents", styles["h1"])]
    for i, s in enumerate(bundle.sections, 1):
        story.append(Paragraph(escape(f"{i}.  {s.title}" + (f"  ({s.note})" if s.note else "")), styles["toc"]))
    if bundle.missing:
        story.append(Spacer(0, 4 * mm))
        story.append(Paragraph(escape("Not generated yet: " + ", ".join(MISSING_TITLES.get(m, m) for m in bundle.missing)), styles["small"]))

    for s in bundle.sections:
        story.append(PageBreak())
        blocks = parse(s.markdown)
        if blocks and blocks[0].kind == "heading" and blocks[0].level == 1:
            blocks = blocks[1:]
        story.append(Paragraph(escape(clean(s.title)), styles["h1"]))
        if s.note:
            story.append(Paragraph(escape(s.note), styles["small"]))
        story += flowables(blocks, styles, width)

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()
