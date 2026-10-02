"""Read one page of the scan's text layer into header, body lines and footnotes.

The text layer comes from OCR of a one-column page. Unlike hist_map's book, its font
sizes follow the glyph heights, so footnotes (set smaller) are told apart by size: they
are the run of small lines at the bottom of the page, starting at a numbered note.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import asdict, dataclass, field

import pymupdf

HEADER_ZONE = 0.13       # header (printed page number) sits in the top 13% of the page
SIGNATURE_ZONE = 0.80    # printer's signature marks ("12") sit below 80%
NOTE_SIZE_RATIO = 0.87   # footnote lines are set at most this size relative to body lines
NOTE_MAX_RATIO = 0.95    # ... except a note's short last line, which the OCR can read a little larger
SUPERSCRIPT_RATIO = 0.72  # note calls are set noticeably smaller than their line
SAME_LINE = 0.5          # fragments overlapping this much vertically are one line

# Characters a running header can be read as: digits, roman numerals and their misreadings.
HEADER_CHARS = set("0123456789IVXLCMivxlcmOoSsGgHhbBzZtTfrWJ»«„*!:;$&<>?()[]{}/\\\"^`")

# A footnote starts with its number: "1.", "2." and their usual OCR misreadings.
NOTE_START = re.compile(r"^\s*(?:\d{1,2}|[iIlt!Sf{]|\*)\s?[.,]\s?")


@dataclass
class Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float

    def as_dict(self) -> dict:
        return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in asdict(self).items()}


@dataclass
class Page:
    pdf: int
    width: float
    height: float
    header: str = ""              # the running header as read, e.g. "— 36 —"
    body: list[Line] = field(default_factory=list)
    notes: list[Line] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)  # signature marks and other noise

    @property
    def body_size(self) -> float:
        sizes = [l.size for l in self.body if len(l.text) >= 10]
        return statistics.median(sizes) if sizes else 0.0


def _span_text(span: dict, line_size: float, first: bool) -> str:
    """A span's text; superscript note calls after a word become " [n]"."""
    text = span["text"]
    t = text.strip()
    if (not first and span["size"] < SUPERSCRIPT_RATIO * line_size and len(t) <= 2
            and (t.isdigit() or t == "*")):
        return f" [{t}]"
    return text


def _raw_lines(page: pymupdf.Page) -> list[dict]:
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            # Keep spans that are only a space: they are the word breaks of the line.
            if any(s["text"].strip() for s in l["spans"]):
                out.append({"bbox": l["bbox"], "spans": l["spans"]})
    return out


def _merge(lines: list[dict]) -> list[dict]:
    """Join fragments that the OCR layer split off one physical line, left to right."""
    lines = sorted(lines, key=lambda l: (l["bbox"][1] + l["bbox"][3]) / 2)
    rows: list[list[dict]] = []
    for l in lines:
        y0, y1 = l["bbox"][1], l["bbox"][3]
        if rows:
            r0 = min(m["bbox"][1] for m in rows[-1])
            r1 = max(m["bbox"][3] for m in rows[-1])
            overlap = min(y1, r1) - max(y0, r0)
            if overlap > SAME_LINE * min(y1 - y0, r1 - r0):
                rows[-1].append(l)
                continue
        rows.append([l])
    merged = []
    for row in rows:
        row.sort(key=lambda m: m["bbox"][0])
        merged.append({
            "bbox": (min(m["bbox"][0] for m in row), min(m["bbox"][1] for m in row),
                     max(m["bbox"][2] for m in row), max(m["bbox"][3] for m in row)),
            "spans": [s for m in row for s in m["spans"]],
        })
    return merged


def _to_line(raw: dict) -> Line:
    spans = raw["spans"]
    # Line size: the median glyph size weighted by characters, ignoring note calls.
    weighted = sorted(s["size"] for s in spans for _ in range(len(s["text"].strip())))
    size = weighted[len(weighted) // 2]
    text = "".join(_span_text(s, size, i == 0) for i, s in enumerate(spans))
    text = re.sub(r"\s+", " ", text).strip()
    x0, y0, x1, y1 = raw["bbox"]
    return Line(text, x0, y0, x1, y1, size)


def _is_header(line: Line, height: float) -> bool:
    """The running header: a short line of digits/roman numerals between dashes."""
    if line.y0 > HEADER_ZONE * height:
        return False
    core = re.sub(r"[\s—–\-_~.,'|]", "", line.text)
    return 0 < len(core) <= 6 and all(c in HEADER_CHARS for c in core)


def _is_signature(line: Line, height: float) -> bool:
    return line.y0 > SIGNATURE_ZONE * height and len(line.text) <= 3 and bool(re.fullmatch(r"[\dIl.*]+", line.text))


def _split_notes(page: Page) -> None:
    """Move the footnotes at the bottom of the page from `body` to `notes`.

    The notes start at a small numbered line in the lower half of the page, below which every
    line is small (a note's short last line can be set a little larger). Small full-width lines
    just above it are a note continued from the previous page.
    """
    body_size = page.body_size
    if not body_size:
        return
    small = NOTE_SIZE_RATIO * body_size
    width = max((l.x1 - l.x0 for l in page.body), default=0)

    def note_like(l: Line) -> bool:
        return l.size < NOTE_MAX_RATIO * body_size or l.x1 - l.x0 < 0.3 * width  # short lines: any size

    start = None
    for i, l in enumerate(page.body):
        rest = page.body[i:]
        if (l.y0 > page.height / 2 and l.size < NOTE_MAX_RATIO * body_size and NOTE_START.match(l.text)
                and all(note_like(r) for r in rest) and sum(r.size < small for r in rest) >= len(rest) / 2):
            start = i
            break
    if start is None:
        # Only a note continued from the previous page: a bottom run of at least two small lines.
        start = len(page.body)
        while start > 0 and page.body[start - 1].size < small:
            start -= 1
        if len(page.body) - start < 2:
            return
    while start > 0 and page.body[start - 1].size < small and page.body[start - 1].x1 - page.body[start - 1].x0 > 0.6 * width:
        start -= 1
    page.notes = page.body[start:]
    page.body = page.body[:start]


def read_page(page: pymupdf.Page, pdf: int, two_columns: bool = False) -> Page:
    out = Page(pdf, page.rect.width, page.rect.height)
    lines = [_to_line(r) for r in _merge(_raw_lines(page))] if not two_columns else _column_lines(page)
    for l in lines:
        if not out.header and not out.body and _is_header(l, out.height):
            out.header = l.text
        elif _is_signature(l, out.height):
            out.dropped.append(l.text)
        else:
            out.body.append(l)
    _split_notes(out)
    return out


def _column_lines(page: pymupdf.Page) -> list[Line]:
    """Lines of a two-column page: header lines first, then the left column, then the right."""
    mid = page.rect.width / 2
    height = page.rect.height
    raw = _raw_lines(page)
    # The running header spans the gutter: keep it whole.
    top = [_to_line(r) for r in raw if r["bbox"][1] <= HEADER_ZONE * height and _is_header(_to_line(r), height)]
    raw = [r for r in raw if not (r["bbox"][1] <= HEADER_ZONE * height and _is_header(_to_line(r), height))]
    # Split each OCR line at the gutter: two-column rows are often read as one line.
    pieces: list[dict] = []
    for l in raw:
        left = [s for s in l["spans"] if s["bbox"][2] <= mid + 10]
        right = [s for s in l["spans"] if s["bbox"][2] > mid + 10]
        for spans in (left, right):
            if spans:
                pieces.append({"bbox": (min(s["bbox"][0] for s in spans), min(s["bbox"][1] for s in spans),
                                        max(s["bbox"][2] for s in spans), max(s["bbox"][3] for s in spans)),
                               "spans": spans})
    lines = [_to_line(r) for r in pieces]
    title = [l for l in lines if l.y0 <= HEADER_ZONE * height and l.x0 < mid < l.x1]
    top += title
    rest = [l for l in lines if l not in title]
    left = _rows([l for l in rest if l.x0 < mid - 40])
    right = _rows([l for l in rest if l.x0 >= mid - 40])
    return sorted(top, key=lambda l: l.y0) + left + right


def _rows(lines: list[Line]) -> list[Line]:
    """Merge the fragments of one column into rows, top to bottom."""
    lines = sorted(lines, key=lambda l: (l.y0 + l.y1) / 2)
    rows: list[Line] = []
    for l in lines:
        if rows:
            r = rows[-1]
            overlap = min(l.y1, r.y1) - max(l.y0, r.y0)
            if overlap > SAME_LINE * min(l.y1 - l.y0, r.y1 - r.y0):
                a, b = (r, l) if r.x0 <= l.x0 else (l, r)
                rows[-1] = Line(a.text + " " + b.text, min(r.x0, l.x0), min(r.y0, l.y0),
                                max(r.x1, l.x1), max(r.y1, l.y1), max(r.size, l.size))
                continue
        rows.append(l)
    return rows
