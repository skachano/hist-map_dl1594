"""Parse the editor's "Corrections et rectifications" into one item per instruction.

Nearly all of them correct the two tables (old forms, printed pp. 175-182; place names,
pp. 183-262). An item is an instruction ("P. 224, art. Lengelsheim, lisez 2144, au lieu de
2145."), the entries it adds or restores (lines after a closing ":"), and the editor's
commentary, which is set in smaller type. Items with a regular pattern are marked `auto`;
Stage 4 applies those and lists the rest for review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from denombrement.text import book, clean

INDENT = 15.0             # pt; an instruction or added entry starts with a first-line indent
COMMENTARY_RATIO = 0.88   # commentary lines are set at most this size relative to instructions

_PAGE = re.compile(r"\bP\.\s*(\d{3})\b")
_INSTRUCTION = re.compile(
    r"(lisez|ajoutez|mettez|menez|placez|intercalez|supprimez|effacez|reportez|rétabli|remplacé|doit venir|"
    r"doit correspondre|ne doit porter|doit être|à effacer|à supprimer|supprimés|accompagné|Au sujet de|^L'art|"
    r"^Les art|^Pour l'art|^Après|^Au (?:lieu|heu)|^A l'art|^Même page|^Plus bas)", re.I)
_ENTRY = re.compile(
    r"^[A-ZÀ-Ýl][^,:]{1,45}(?:,\s*(?:vil|v\.i|ham|canton|ferme|section|grand|com|eom|coin|cens)|"
    r"\.\s*(?:Voy\.|[A-ZÀ-Ýl])|,\s*aliàs)")
_REPLACE = re.compile(r"a[nu] (?:lieu|heu) de\s+(?P<old>.+?),?\s+lisez\s*:?\s*(?P<new>.+?)\.?$", re.I)
_RENUMBER = re.compile(r"lisez\s*:?\s*(?P<new>\d{3,4}),?\s+a[nu] (?:lieu|heu) de\s+(?P<old>\d{3,4})", re.I)
_RENUMBER2 = re.compile(r"a[nu] (?:lieu|heu) de\s+(?P<old>\d{3,4}),?\s+lisez\s*:?\s*(?P<new>\d{3,4})", re.I)
_ARTICLE = re.compile(r"(?:l'art\.?|art\.|l'article)\s*(?P<x>[A-ZÀ-Ýl][\w'’\- ]+?)(?=[,.(]|\s+(?:de|doit|qui|même|et)\b)")


@dataclass
class Correction:
    no: int
    page: str                 # the corrections page it is printed on ("c3")
    target_page: str = ""     # the printed page it corrects
    target: str = ""          # old-forms, index, introduction
    article: str = ""
    action: str = "other"     # replace, renumber, add, delete, move, note, other
    old: str = ""
    new: str = ""
    entries: list[str] = field(default_factory=list)   # added or restored table entries
    commentary: str = ""
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return clean.dehyphenate(self.lines)

    @property
    def auto(self) -> bool:
        if self.action == "renumber":
            return bool(self.new and (self.old or self.article))
        if self.action == "replace":
            return bool(self.old and self.new) or bool(self.entries)
        if self.action == "add":
            return bool(self.entries)
        if self.action == "delete":
            return bool(self.article)
        return False

    def as_row(self) -> dict:
        return {
            "no": self.no, "page": self.page, "target_page": self.target_page, "target": self.target,
            "article": self.article, "action": self.action, "old": self.old, "new": self.new,
            "entries": " | ".join(self.entries), "auto": int(self.auto), "text": self.text,
            "commentary": self.commentary,
        }


def _target(page: str) -> str:
    if not page.isdigit():
        return ""
    p = int(page)
    if book.OLD_FORMS_PRINTED[0] <= p <= book.OLD_FORMS_PRINTED[1]:
        return "old-forms"
    if book.INDEX_PRINTED[0] <= p <= book.INDEX_PRINTED[1]:
        return "index"
    return "text"


def _instruction(c: Correction) -> str:
    """The instruction itself, without the entries it adds."""
    return clean.dehyphenate([l for l in c.lines if l not in c.entries])


def _classify(c: Correction) -> None:
    text = _instruction(c)
    low = text.lower()
    if (m := _RENUMBER.search(text) or _RENUMBER2.search(text)):
        c.action, c.old, c.new = "renumber", m.group("old"), m.group("new")
    elif (m := re.search(r"ajoutez à l'art\.?\s*(?P<x>[A-ZÀ-Ýl][\w'’\-]+) le n\S*\s*(?P<n>\d{3,4})", text)):
        c.action, c.article, c.new = "renumber", m.group("x"), m.group("n")
        return
    elif re.search(r"doit correspondre|ne doit porter que|le n[°o\"]+\s*\d|numéro doit être effacé", low):
        c.action = "renumber"
        if (m := re.search(r"au n\S*\s*(\d{3,4}),?\s+e[lt] non au\s+(\d{3,4})", text)):
            c.new, c.old = m.group(1), m.group(2)
        elif (m := re.search(r"ne doit porter que le n\S*\s*(\d{3,4})\s*;\s*le\s+(\d{3,4})", text)):
            c.new, c.old = m.group(1), m.group(2)  # keep only the first number; the second goes elsewhere
    elif (m := _REPLACE.search(text)):
        new = m.group("new").strip(" ,.")
        new = new.rsplit(":", 1)[-1] if ":" in new else new           # "(en supprimant la note) : Selbach"
        new = re.sub(r",\s*en supprimant.*$", "", new).strip(" ,.")  # "…, en supprimant la note"
        c.action, c.old, c.new = "replace", m.group("old").strip(" ,"), new
    elif re.search(r"rétabli|remplacé par le suivant|doit être remplacé", low):
        c.action = "replace"
    elif re.search(r"ajoutez|mettez|menez|placez|intercalez|en t[eê]te de la lettre", low):
        c.action = "add"
    elif re.search(r"supprimez|effacez|supprimés|est à effacer", low):
        c.action = "delete"
    elif re.search(r"doit venir|reportez", low):
        c.action = "move"
    elif re.search(r"accompagné de cette note|voy\. la note", low):
        c.action = "note"
    if (m := re.match(r"P\.\s*\d{3}[.,]\s*([A-ZÀ-Ý][\w'’\-]+),\s", text)) and not _INSTRUCTION.match(m.group(1)):
        c.article = m.group(1)  # "P. 190, Bethingen, de la 5e ligne, …"
    elif c.action == "move" and (m := re.match(r"([A-ZÀ-Ý][\w'’\-]+).*?apr[eè]s\s+([A-ZÀ-Ý][\w'’\-]+)", text)):
        c.article, c.new = m.group(1), f"après {m.group(2)}"
    elif (m := _ARTICLE.search(text)):
        c.article = m.group("x").strip()
    elif c.action == "delete" and (m := re.search(r"(?:supprimez|effacez)\s*(?:l'art\.?\s*)?([A-ZÀ-Ýl][\w'’\-]+)", text, re.I)):
        c.article = m.group(1)
    elif c.action == "delete" and (m := re.match(r"([A-ZÀ-Ý][\w'’\-]+)\s*\(p\.\s*\d+\)\s*est à effacer", text)):
        c.article = m.group(1)
    elif c.action in ("add", "move") and (m := re.search(r"après (?:l'art\.?\s*|celui de\s+)?([A-ZÀ-Ýl][\w'’\-]+)", text)):
        c.article = m.group(1)
    elif c.action == "move" and (m := re.match(r"([A-ZÀ-Ý][\w'’\-]+)", text)):
        c.article = m.group(1)


def parse(lines) -> list[Correction]:
    """`lines` holds (page record, line, cleaned text) for the corrections part."""
    items: list[Correction] = []
    collecting = False   # after an instruction ending with ":", indented entry-shaped lines are entries
    sizes = sorted(l.size for _, l, _ in lines if len(l.text) > 20)
    body_size = sizes[len(sizes) // 2] if sizes else 0
    lefts: dict[str, float] = {}
    for rec, line, _ in lines:
        lefts.setdefault(rec.label, []).append(line.x0)
    left = {page: sorted(xs)[len(xs) // 10] for page, xs in lefts.items()}  # per page: the scan shifts
    target_page = ""
    for rec, line, text in lines:
        if text.startswith(("CORRECTIONS ET", "Maney, imp", "Nancy, imp")):
            continue
        if not items and not _PAGE.search(text):
            continue  # the editor's preamble
        indented = line.x0 > left[rec.label] + INDENT
        if line.size < COMMENTARY_RATIO * body_size and items:
            c = items[-1]
            c.commentary = clean.dehyphenate([c.commentary, text]) if c.commentary else text
            continue
        if items and items[-1].target == "introduction":
            items[-1].lines.append(text)  # the closing observation on the introduction, to the end
            continue
        if indented and collecting and _ENTRY.match(text) and not _INSTRUCTION.search(text) and not _PAGE.match(text):
            items[-1].entries.append(text)
            items[-1].lines.append(text)
            continue
        if indented:
            if (m := _PAGE.search(text)):
                target_page = m.group(1)
            items.append(Correction(len(items) + 1, rec.label or "", target_page, _target(target_page)))
            if re.match(r"Au sujet de l'intro", text):
                items[-1].target, items[-1].target_page = "introduction", ""
            items[-1].lines.append(text)
            collecting = text.rstrip().endswith((":", ";"))
            continue
        # A continuation line: of the last added entry, or of the instruction.
        c = items[-1]
        if c.entries and c.lines[-1] == c.entries[-1]:
            c.entries[-1] = clean.dehyphenate([c.entries[-1], text])
            c.lines[-1] = c.entries[-1]
        else:
            c.lines.append(text)
            collecting = collecting or text.rstrip().endswith((":", ";"))
    for c in items:
        # "Titling, mis à la p. 252, …", "Urexweiler (p. 254) est à effacer": the page is in the text.
        if (m := re.match(r"[A-ZÀ-Ý][\w'’\-]+(?:, mis à la p\.|\s*\(p\.)\s*(\d{3})", c.text)):
            c.target_page = m.group(1)
            c.target = _target(c.target_page)
        if c.target == "introduction":
            c.action = "note"
            continue
        _classify(c)
    return items
