"""Stage 1 orchestrator: PDF -> pages.jsonl, parts/, index.csv, old_forms.csv, corrections.csv."""
from __future__ import annotations

import csv
import json
import re
import shutil
from dataclasses import dataclass, field

import pymupdf

from denombrement import config
from denombrement.text import book, clean, corrections, indexes, layout, ocr, pagemap

OUT_PAGES = config.RAW_DIR / "pages.jsonl"
OUT_PARTS = config.RAW_DIR / "parts"
OUT_INDEX = config.RAW_DIR / "index.csv"
OUT_OLD_FORMS = config.RAW_DIR / "old_forms.csv"
OUT_CORRECTIONS = config.RAW_DIR / "corrections.csv"


@dataclass
class PageRecord:
    page: layout.Page
    label: str | None
    parts: list[str] = field(default_factory=list)       # part of each body line
    clean: list[str] = field(default_factory=list)       # cleaned text of each body line


def assign_parts(pages: list[layout.Page]) -> dict[int, list[str]]:
    """The part each body line belongs to, per PDF page."""
    starts = {pdf: [] for pdf in range(1, book.LAST_PDF + 1)}
    for part, pdf, pattern in book.PARTS:
        starts[pdf].append((part, pattern))
    current = None
    out: dict[int, list[str]] = {}
    for p in pages:
        here = list(starts.get(p.pdf, []))
        if here and here[0][1] is None:
            current = here.pop(0)[0]
        ids = []
        for line in p.body:
            if here and re.search(here[0][1], line.text):
                current = here.pop(0)[0]
            ids.append(current)
        if here:
            raise ValueError(f"PDF {p.pdf}: the start of part(s) {[h[0] for h in here]} was not found")
        out[p.pdf] = ids
    return out


def note_texts(lines: list[layout.Line]) -> list[str]:
    """Group a page's footnote lines into notes (a note starts with its number)."""
    notes: list[list[str]] = []
    for l in lines:
        if layout.NOTE_START.match(l.text) or not notes:
            notes.append([])
        notes[-1].append(l.text)
    return [clean.dehyphenate(n) for n in notes]


def write_parts(records: list[PageRecord]) -> list[str]:
    if OUT_PARTS.exists():
        shutil.rmtree(OUT_PARTS)
    OUT_PARTS.mkdir(parents=True)
    order = {part: i for i, (part, _, _) in enumerate(book.PARTS)}
    body: dict[str, list[str]] = {}
    notes: dict[str, list[str]] = {}
    for r in records:
        seen: set[str] = set()
        for part, text in zip(r.parts, r.clean):
            if part is None:
                continue
            if part not in seen:
                body.setdefault(part, []).append(f"[p. {r.label}]")
                seen.add(part)
            body[part].append(text)
        if r.page.notes and r.parts:
            last = next((p for p in reversed(r.parts) if p), None)
            if last:
                notes.setdefault(last, []).append(f"[p. {r.label}]")
                notes[last].extend(note_texts(r.page.notes))
    names = []
    for part, lines in body.items():
        name = f"{order[part]:02d}-{part}"
        (OUT_PARTS / f"{name}.txt").write_text("\n".join(lines) + "\n")
        if part in notes:
            (OUT_PARTS / f"{name}-notes.txt").write_text("\n".join(notes[part]) + "\n")
        names.append(name)
    return names


def part_lines(records: list[PageRecord], part: str) -> list[tuple[PageRecord, layout.Line, str]]:
    """The body lines of one part, with their page and cleaned text."""
    return [(r, l, t) for r in records for l, p, t in zip(r.page.body, r.parts, r.clean) if p == part]


def write_csv(path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def run() -> None:
    doc = pymupdf.open(config.source_pdf())
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    pages = [layout.read_page(doc[n - 1], n, n in book.TWO_COLUMN_PAGES) for n in range(1, book.LAST_PDF + 1)]
    parts = assign_parts(pages)
    records = []
    for p in pages:
        label = pagemap.printed(p.pdf)
        cleaned = [clean.fix_ocr(l.text) for l in p.body]
        records.append(PageRecord(p, label, parts[p.pdf], cleaned))

    with OUT_PAGES.open("w") as f:
        for r in records:
            f.write(json.dumps({
                "pdf": r.page.pdf, "printed": r.label, "header": r.page.header,
                "header_ok": pagemap.agrees(r.page.header, r.label) if r.label and r.page.header else None,
                "body": [{**l.as_dict(), "clean": t, "part": p} for l, t, p in zip(r.page.body, r.clean, r.parts)],
                "notes": [l.as_dict() for l in r.page.notes],
                "dropped": r.page.dropped,
            }, ensure_ascii=False) + "\n")

    checked = [pagemap.agrees(r.page.header, r.label) for r in records if r.label and r.page.header]
    garbled = [r for r in records if r.label and r.page.header and pagemap.agrees(r.page.header, r.label) is False]
    # A header that reads as a neighbouring page number would mean a missing or extra page.
    shifted = [r for r in garbled if r.label.isdigit() and any(
        pagemap.agrees(r.page.header, str(int(r.label) + d)) for d in (-2, -1, 1, 2))]
    print(f"page map: {sum(c is True for c in checked)} headers agree, {len(garbled)} garbled, "
          f"{len(shifted)} point to another offset, "
          f"{sum(1 for r in records if r.label and not r.page.header)} pages without a header")
    by_pdf = {r.page.pdf: r for r in records}
    for r in shifted:
        # The nearest readable headers on both sides agreeing with their labels confirm the offset.
        def nearest(step: int) -> bool:
            for n in range(r.page.pdf + step, r.page.pdf + 4 * step, step):
                other = by_pdf.get(n)
                if other and other.label and other.page.header:
                    verdict = pagemap.agrees(other.page.header, other.label)
                    if verdict is not False:
                        return bool(verdict)
            return False

        confirmed = nearest(-1) and nearest(1)
        print(f"  PDF {r.page.pdf}: expected {r.label}, header {r.page.header!r}"
              + (" (neighbours confirm the offset)" if confirmed else " — CHECK"))

    names = write_parts(records)
    print(f"parts: {len(names)} -> {OUT_PARTS.relative_to(config.ROOT)}/")

    def reread(pdf: int, line: layout.Line) -> str:
        return ocr.read_line(doc[pdf - 1], (line.x0, line.y0, line.x1, line.y1))

    index_rows = indexes.parse_index(part_lines(records, "index"),
                                     {r.label: note_texts(r.page.notes) for r in records if r.label}, reread)
    write_csv(OUT_INDEX, [e.as_row() for e in index_rows])
    print(f"index: {len(index_rows)} entries, {sum(e.numbers_ok for e in index_rows)} with clean numbers "
          f"({sum(e.numbers_source == 'tesseract' for e in index_rows)} read again by Tesseract), "
          f"{sum(not e.identified for e in index_rows)} unidentified -> {OUT_INDEX.name}")

    old = indexes.parse_old_forms(part_lines(records, "old-forms"))
    write_csv(OUT_OLD_FORMS, [o.as_row() for o in old])
    print(f"old forms: {len(old)} -> {OUT_OLD_FORMS.name}")

    corr = corrections.parse(part_lines(records, "corrections"))
    write_csv(OUT_CORRECTIONS, [c.as_row() for c in corr])
    kinds = {}
    for c in corr:
        kinds[c.action] = kinds.get(c.action, 0) + 1
    print(f"corrections: {len(corr)} items {dict(sorted(kinds.items()))}, "
          f"{sum(c.auto for c in corr)} machine-applicable -> {OUT_CORRECTIONS.name}")
