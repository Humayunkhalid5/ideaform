"""Draw the blueprint's Mermaid diagrams for PDF and Word without a browser.

``render.py`` writes a small, regular Mermaid subset (``flowchart LR/TD`` with quoted node
labels and ``-->`` edges, and ``erDiagram`` with entity blocks and relationships). This module
parses that subset and lays it out with ReportLab graphics: layered boxes and arrows for
flowcharts, a grid of tables with labelled links for ER diagrams. Anything it cannot parse
(for example a diagram the user rewrote by hand) returns ``None`` and the caller prints the
source instead, so nothing is silently lost.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field

from reportlab.graphics.shapes import Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib import colors

INK = colors.HexColor("#14213d")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#94a3b8")
FILLS = {
    "process": colors.HexColor("#eef2ff"),
    "store": colors.HexColor("#e6f2f1"),
    "external": colors.HexColor("#f1f5f9"),
    "ai": colors.HexColor("#f8ece5"),
    "queue": colors.HexColor("#fef7e6"),
}
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


@dataclass
class Flowchart:
    direction: str
    nodes: dict[str, tuple[str, str]] = field(default_factory=dict)  # id -> (label, kind)
    edges: list[tuple[str, str, str]] = field(default_factory=list)


@dataclass
class ErDiagram:
    entities: dict[str, list[str]] = field(default_factory=dict)  # NAME -> ["uuid id PK", ...]
    relations: list[tuple[str, str, str, str]] = field(default_factory=list)  # a, card_a, b, card_b+label


_NODE = re.compile(
    r'^\s*([A-Za-z][\w]*)\s*(\[\(|\(\[|\[/|\{\{|\[|\()\s*"?(.*?)"?\s*(\)\]|\]\)|/\]|\}\}|\]|\))\s*$'
)
_EDGE = re.compile(r'^\s*([A-Za-z][\w]*)\s*-->\s*(?:\|"?(.*?)"?\|\s*)?([A-Za-z][\w]*)\s*$')
_REL = re.compile(r'^\s*(\w+)\s+(\|\||\}o|\|o|o\||\}\|)--(\|\||o\{|\|\{|o\||\|o)\s+(\w+)\s*:\s*"?(.*?)"?\s*$')
_SHAPE_KIND = {"[(": "store", "([": "external", "[/": "queue", "{{": "ai", "[": "process", "(": "process"}


def parse(code: str) -> Flowchart | ErDiagram | None:
    lines = [ln.rstrip() for ln in code.strip().splitlines() if ln.strip() and not ln.strip().startswith("%%")]
    if not lines:
        return None
    head = lines[0].strip().split()
    if head[0] in ("flowchart", "graph"):
        chart = Flowchart(direction=(head[1] if len(head) > 1 else "TD").upper())
        for line in lines[1:]:
            if m := _EDGE.match(line):
                a, label, b = m.groups()
                for n in (a, b):
                    chart.nodes.setdefault(n, (n, "process"))
                chart.edges.append((a, b, label or ""))
            elif m := _NODE.match(line):
                node, left, label, _right = m.groups()
                chart.nodes[node] = (label, _SHAPE_KIND.get(left, "process"))
            else:
                return None
        return chart if chart.nodes else None
    if head[0] == "erDiagram":
        er = ErDiagram()
        current: str | None = None
        for line in lines[1:]:
            s = line.strip()
            if current is not None:
                if s == "}":
                    current = None
                else:
                    er.entities[current].append(s)
                continue
            if s.endswith("{"):
                current = s[:-1].strip()
                er.entities[current] = []
            elif m := _REL.match(s):
                a, left, right, b, label = m.groups()
                er.relations.append((a, _card(left), b, f"{_card(right)}|{label}"))
            else:
                return None
        return er if er.entities else None
    return None


def _card(token: str) -> str:
    return "1" if token in ("||", "|o", "o|") else "N"


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=width, break_long_words=True)[:4] or [""]


def _arrow(group: Group, x1: float, y1: float, x2: float, y2: float, label: str = "") -> None:
    group.add(Line(x1, y1, x2, y2, strokeColor=LINE, strokeWidth=0.9))
    import math

    angle = math.atan2(y2 - y1, x2 - x1)
    size = 5
    p1 = (x2 - size * math.cos(angle - 0.4), y2 - size * math.sin(angle - 0.4))
    p2 = (x2 - size * math.cos(angle + 0.4), y2 - size * math.sin(angle + 0.4))
    group.add(Polygon([x2, y2, *p1, *p2], fillColor=LINE, strokeColor=LINE, strokeWidth=0.5))
    if label:
        # 62% along the edge: labels of edges fanning out from one node no longer stack up
        mx, my = x1 + (x2 - x1) * 0.62, y1 + (y2 - y1) * 0.62
        text = label if len(label) <= 28 else label[:27] + "…"
        w = len(text) * 3.6 + 6
        group.add(Rect(mx - w / 2, my - 5, w, 10, fillColor=colors.white, strokeColor=None))
        group.add(String(mx, my - 2.5, text, fontName=FONT, fontSize=6.5, fillColor=MUTED, textAnchor="middle"))


def _layers(chart: Flowchart) -> dict[str, int]:
    """Longest-path layering (cycle safe: at most len(nodes) relaxation rounds)."""
    layer = {n: 0 for n in chart.nodes}
    for _ in range(len(chart.nodes)):
        changed = False
        for a, b, _l in chart.edges:
            if a != b and layer[b] < layer[a] + 1 and layer[a] + 1 < len(chart.nodes):
                layer[b] = layer[a] + 1
                changed = True
        if not changed:
            break
    return layer


def draw_flowchart(chart: Flowchart) -> Drawing:
    w, gap_main, gap_cross = 118, 46, 16
    layer = _layers(chart)
    columns: dict[int, list[str]] = {}
    for node in chart.nodes:
        columns.setdefault(layer[node], []).append(node)
    sizes = {n: (w, 12 + 9 * len(_wrap(chart.nodes[n][0], 24))) for n in chart.nodes}
    horizontal = chart.direction in ("LR", "RL")
    pos: dict[str, tuple[float, float]] = {}
    if horizontal:
        heights = {c: sum(sizes[n][1] for n in ns) + gap_cross * (len(ns) - 1) for c, ns in columns.items()}
        total_h = max(heights.values())
        for c, ns in columns.items():
            y = (total_h + heights[c]) / 2
            for n in ns:
                h = sizes[n][1]
                y -= h
                pos[n] = (c * (w + gap_main), y)
                y -= gap_cross
        total_w = (max(columns) + 1) * (w + gap_main) - gap_main
    else:
        row_h = {c: max(sizes[n][1] for n in ns) for c, ns in columns.items()}
        widths = {c: len(ns) * w + gap_cross * (len(ns) - 1) for c, ns in columns.items()}
        total_w = max(widths.values())
        total_h = sum(row_h.values()) + gap_main * (len(columns) - 1)
        y_top = total_h
        for c in sorted(columns):
            x = (total_w - widths[c]) / 2
            for n in columns[c]:
                pos[n] = (x, y_top - row_h[c])
                x += w + gap_cross
            y_top -= row_h[c] + gap_main
    group = Group()
    for a, b, label in chart.edges:
        if a not in pos or b not in pos or a == b:
            continue
        (ax, ay), (bx, by) = pos[a], pos[b]
        aw, ah = sizes[a]
        bw, bh = sizes[b]
        if horizontal:
            _arrow(group, ax + aw, ay + ah / 2, bx, by + bh / 2, label)
        else:
            _arrow(group, ax + aw / 2, ay, bx + bw / 2, by + bh, label)
    for node, (x, y) in pos.items():
        label, kind = chart.nodes[node]
        bw, bh = sizes[node]
        group.add(Rect(x, y, bw, bh, rx=5, ry=5, fillColor=FILLS.get(kind, FILLS["process"]),
                       strokeColor=INK if kind != "external" else LINE, strokeWidth=0.7,
                       strokeDashArray=[2, 2] if kind == "external" else None))
        lines = _wrap(label, 24)
        start = y + bh / 2 + (len(lines) - 1) * 4.5 - 2.5
        for i, text in enumerate(lines):
            group.add(String(x + bw / 2, start - i * 9, text, fontName=FONT, fontSize=7.5, fillColor=INK, textAnchor="middle"))
    return _fit(group, total_w, total_h)


def draw_er(er: ErDiagram) -> Drawing:
    w, header, row, gap, per_row = 150, 15, 10.5, 36, 3
    max_rows = 12
    names = list(er.entities)
    heights = {n: header + row * (min(len(er.entities[n]), max_rows) + (1 if len(er.entities[n]) > max_rows else 0)) + 4 for n in names}
    grid = [names[i:i + per_row] for i in range(0, len(names), per_row)]
    row_heights = [max(heights[n] for n in r) for r in grid]
    total_w = min(per_row, len(names)) * (w + gap) - gap
    total_h = sum(row_heights) + gap * (len(grid) - 1)
    pos: dict[str, tuple[float, float]] = {}
    y_top = total_h
    for r, members in enumerate(grid):
        for i, n in enumerate(members):
            pos[n] = (i * (w + gap), y_top - heights[n])
        y_top -= row_heights[r] + gap
    group = Group()

    def edge_point(n: str, tx: float, ty: float) -> tuple[float, float]:
        x, y = pos[n]
        h = heights[n]
        cx, cy = x + w / 2, y + h / 2
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        scale = min((w / 2) / abs(dx) if dx else float("inf"), (h / 2) / abs(dy) if dy else float("inf"))
        return cx + dx * scale, cy + dy * scale

    for a, card_a, b, rest in er.relations:
        if a not in pos or b not in pos:
            continue
        card_b, label = rest.split("|", 1)
        (ax, ay), (bx, by) = pos[a], pos[b]
        acx, acy = ax + w / 2, ay + heights[a] / 2
        bcx, bcy = bx + w / 2, by + heights[b] / 2
        p1 = edge_point(a, bcx, bcy)
        p2 = edge_point(b, acx, acy)
        group.add(Line(*p1, *p2, strokeColor=LINE, strokeWidth=0.9))
        group.add(String(p1[0] + (4 if p2[0] >= p1[0] else -8), p1[1] + 3, card_a, fontName=FONT_BOLD, fontSize=7, fillColor=MUTED))
        group.add(String(p2[0] + (4 if p1[0] >= p2[0] else -8), p2[1] + 3, card_b, fontName=FONT_BOLD, fontSize=7, fillColor=MUTED))
        if label:
            mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            text = label[:24]
            tw = len(text) * 3.6 + 6
            group.add(Rect(mx - tw / 2, my - 5, tw, 10, fillColor=colors.white, strokeColor=None))
            group.add(String(mx, my - 2.5, text, fontName=FONT, fontSize=6.5, fillColor=MUTED, textAnchor="middle"))
    for n, (x, y) in pos.items():
        h = heights[n]
        group.add(Rect(x, y, w, h, fillColor=colors.white, strokeColor=INK, strokeWidth=0.7))
        group.add(Rect(x, y + h - header, w, header, fillColor=FILLS["store"], strokeColor=INK, strokeWidth=0.7))
        group.add(String(x + w / 2, y + h - header + 4.5, n[:26], fontName=FONT_BOLD, fontSize=7.5, fillColor=INK, textAnchor="middle"))
        fields = er.entities[n]
        shown = fields[:max_rows] + ([f"… {len(fields) - max_rows} more"] if len(fields) > max_rows else [])
        for i, f in enumerate(shown):
            group.add(String(x + 5, y + h - header - row * (i + 1) + 1.5, f[:34], fontName=FONT, fontSize=6.8, fillColor=INK))
    return _fit(group, total_w, total_h)


def _fit(group: Group, width: float, height: float, max_w: float = 480, max_h: float = 620) -> Drawing:
    pad = 6
    scale = min(1.0, max_w / (width + 2 * pad), max_h / (height + 2 * pad))
    group.translate(pad, pad)
    outer = Group(group)
    outer.scale(scale, scale)
    drawing = Drawing((width + 2 * pad) * scale, (height + 2 * pad) * scale)
    drawing.add(outer)
    return drawing


def drawing_for(code: str) -> Drawing | None:
    """A drawing for Mermaid ``code``, or None when it is outside the supported subset."""
    try:
        parsed = parse(code)
        if isinstance(parsed, Flowchart):
            return draw_flowchart(parsed)
        if isinstance(parsed, ErDiagram):
            return draw_er(parsed)
    except Exception:  # noqa: BLE001 - fall back to printing the source
        return None
    return None


def png_for(code: str, dpi: int = 160) -> bytes | None:
    drawing = drawing_for(code)
    if drawing is None:
        return None
    try:
        from reportlab.graphics import renderPM

        return renderPM.drawToString(drawing, fmt="PNG", dpi=dpi)
    except Exception:  # noqa: BLE001 - optional renderer missing
        return None
