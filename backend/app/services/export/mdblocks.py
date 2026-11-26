"""Markdown -> a small block tree that both the PDF and the Word writers render.

Parsed with markdown-it-py (CommonMark + tables). Raw HTML is disabled, so text from the
model or the user can never inject markup into the documents.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from markdown_it import MarkdownIt


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    href: str | None = None


@dataclass
class Block:
    kind: str  # heading, paragraph, list, table, code, quote, hr
    level: int = 0
    runs: list[Run] = field(default_factory=list)
    ordered: bool = False
    items: list[list["Block"]] = field(default_factory=list)
    header: list[list[Run]] = field(default_factory=list)
    rows: list[list[list[Run]]] = field(default_factory=list)
    lang: str = ""
    text: str = ""
    children: list["Block"] = field(default_factory=list)


_MD = MarkdownIt("commonmark", {"html": False}).enable("table")


def _inline(token) -> list[Run]:
    runs: list[Run] = []
    bold = italic = False
    href: str | None = None
    for child in token.children or []:
        t = child.type
        if t == "text":
            runs.append(Run(child.content, bold, italic, False, href))
        elif t == "code_inline":
            runs.append(Run(child.content, bold, italic, True, href))
        elif t in ("softbreak", "hardbreak"):
            runs.append(Run("\n" if t == "hardbreak" else " ", bold, italic, False, href))
        elif t == "strong_open":
            bold = True
        elif t == "strong_close":
            bold = False
        elif t == "em_open":
            italic = True
        elif t == "em_close":
            italic = False
        elif t == "link_open":
            href = child.attrs.get("href")
        elif t == "link_close":
            href = None
        elif t == "image":
            runs.append(Run(f"[image: {child.content or child.attrs.get('alt', '')}]", bold, True))
        elif child.content:
            runs.append(Run(child.content, bold, italic, False, href))
    return runs


def _parse(tokens, i: int, stop: str | None) -> tuple[list[Block], int]:
    blocks: list[Block] = []
    while i < len(tokens):
        tok = tokens[i]
        t = tok.type
        if stop and t == stop:
            return blocks, i + 1
        if t == "heading_open":
            blocks.append(Block("heading", level=int(tok.tag[1]), runs=_inline(tokens[i + 1])))
            i += 3
        elif t == "paragraph_open":
            blocks.append(Block("paragraph", runs=_inline(tokens[i + 1])))
            i += 3
        elif t in ("bullet_list_open", "ordered_list_open"):
            ordered = t == "ordered_list_open"
            close = "ordered_list_close" if ordered else "bullet_list_close"
            block = Block("list", ordered=ordered)
            i += 1
            while tokens[i].type != close:
                if tokens[i].type == "list_item_open":
                    item, i = _parse(tokens, i + 1, "list_item_close")
                    block.items.append(item)
                else:
                    i += 1
            blocks.append(block)
            i += 1
        elif t == "table_open":
            block = Block("table")
            i += 1
            in_head = False
            row: list[list[Run]] = []
            while tokens[i].type != "table_close":
                tt = tokens[i].type
                if tt == "thead_open":
                    in_head = True
                elif tt == "thead_close":
                    in_head = False
                elif tt == "tr_open":
                    row = []
                elif tt in ("th_open", "td_open"):
                    row.append(_inline(tokens[i + 1]))  # cell content, then skip its close tag
                    i += 2
                elif tt == "tr_close":
                    if in_head and not block.header:
                        block.header = row
                    else:
                        block.rows.append(row)
                i += 1
            blocks.append(block)
            i += 1
        elif t in ("fence", "code_block"):
            blocks.append(Block("code", lang=(tok.info or "").strip().split(" ")[0].lower(), text=tok.content.rstrip("\n")))
            i += 1
        elif t == "blockquote_open":
            children, i = _parse(tokens, i + 1, "blockquote_close")
            blocks.append(Block("quote", children=children))
        elif t == "hr":
            blocks.append(Block("hr"))
            i += 1
        else:
            i += 1
    return blocks, i


def parse(markdown: str) -> list[Block]:
    blocks, _ = _parse(_MD.parse(markdown or ""), 0, None)
    return blocks


def plain(runs: list[Run]) -> str:
    return "".join(r.text for r in runs)
