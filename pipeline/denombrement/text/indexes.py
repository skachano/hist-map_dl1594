"""Parse the editor's two tables: the place-name index and the table of old forms.

Index entry: `Beckingen, vil. (commanderie), com. de Haustadt, canton de Merzig, 1450, 2485.`
The trailing numbers are the Dénombrement's entry numbers, abbreviated after the first:
`1475, 1537, 38` is 1538, `2240, 67` is 2267; `709-715` is a range.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from denombrement.text import book, clean

CONTINUATION_INDENT = 12.0  # pt; continuation lines of an entry are indented

# OCR misreadings of digits in the entry numbers.
_DIGIT = str.maketrans({"O": "0", "o": "0", "Q": "0", "D": "0", "l": "1", "I": "1", "i": "1", "!": "1", "|": "1",
                        "î": "1", "ï": "1", "t": "1", "f": "1", "J": "1", "j": "1", "G": "6", "S": "5", "s": "5",
                        "B": "8", "z": "2", "Z": "2", "q": "9", "g": "9"})
_NUMERIC = re.compile(r"^[\dOoQDlIi!|îïtfJjGSsBzZqg»«>?:*]{1,5}$")

_KINDS = (  # index abbreviations for the kind of place
    "anc.", "vil.", "ham.", "ferme", "censé", "cense", "chat.", "château", "faubourg", "moulin", "gagnage",
    "écart", "maison", "rente", "section", "chapelle", "abbaye", "prieuré", "forêt", "bourg", "ville",
)
_COMMUNE = re.compile(r"^(?:com|corn|coin|eom|cora|cotn|conn|c0m|rom)[.,]?\s*(?:d[e'’]\s*|du\s+)(?P<x>.+)$", re.I)
_CANTON = re.compile(r"^canton\s*(?:d[e'’]\s*|du\s+)?(?P<x>.*)$", re.I)
_CHEF_LIEU = re.compile(r"^[ce]h\.?\s*-?\s*l\.?\s*d(?:[e'’u]|es)\b", re.I)
_NEAR = re.compile(r"^(?:.*\s)?pr[eéè]s\s+(?:de\s+|d[’']\s*)(?P<x>.+)$", re.I)

# OCR variants of the index's recurring words, normalized before the entry is split.
_FIXES = [
    (re.compile(r"\b(?:canton|canlon|canion|cantou|caalon|canlou|eanton|cauton|caoton|cantoa|canlon)\s*(?=d[e'’u]|\w)"), "canton "),
    (re.compile(r"\b(?:com|corn|coin|eom|cora|cotn|conn|c0m|rom|eorn|coni)\s*[.,]\s*(?=d[e'’u])"), "com. "),
    (re.compile(r"\b1er canton\b"), "canton"),
    (re.compile(r"\s*[.\\]\s+(?=(?:canton|com\.|ham\.|vil\.|Voy\.)\s)"), ", "),   # "Weiskirch. canton de …"
    (re.compile(r"(?<=[\w)])\s+(?=(?:canton|com\.)\s+d)"), ", "),                   # "Clerjus (le) canton de …"
    (re.compile(r"(?<=[\w)])\s*[.;]\s+(?=\d)"), ", "),                               # "(Moselle). 1969"
    (re.compile(r"(?<=[a-zéè)])\s+(?=\d{2,4}[.,]?\s*$)"), ", "),                      # "Sarreguemines 1584."
]


def normalize(text: str) -> str:
    for pattern, repl in _FIXES:
        text = pattern.sub(repl, text)
    return text
_ARR = re.compile(r"^(?:arr|air)\.?\s*(?:d[e'’]\s*)?(?P<x>.+)$", re.I)
_XREF = re.compile(r"^(?:Voy|Yoy|Vov)\.?\s*(?P<x>.+)$")
_REGION = re.compile(r"\(([^()]*(?:Meur\S*|M[cr]?eurth\S*|Mo[sz]\S*le|Meus\S*|Vosg\S*|Marne|Rhin|Pr\s*\.?|Bav\S*|Luxemb\S*|Sa[oô]ne)[^()]*)\)[\s.;,]*$")
_REGION_NAMES = [("Meurthe", r"^m\S*u\S*r"), ("Moselle", r"^mo"), ("Meuse", r"^meus|^mcus"), ("Vosges", r"^vosg"),
                 ("Haute-Marne", r"marne"), ("Bas-Rhin", r"^bas"), ("Haut-Rhin", r"^haut-?rhin"), ("Pr.", r"^pr"),
                 ("Bav.", r"^bav"), ("Luxembourg", r"^luxemb"), ("Haute-Saône", r"sa[oô]ne")]


def region_name(text: str) -> str:
    """The département or state an index line gives, its OCR misspellings mended ("Meurthc")."""
    t = text.strip(" .;,").lower()
    for name, pattern in _REGION_NAMES:
        if re.search(pattern, t):
            return name
    return text.strip()
_STATE = re.compile(r"(grand[- ]duché d'Oldenbourg|grand[- ]duché de Luxembourg|Luxembourg)", re.I)


@dataclass
class IndexEntry:
    page: str
    text: str
    name: str = ""
    marker: str = ""          # note call after the name ("1", "*")
    kind: str = ""
    commune: str = ""
    canton: str = ""
    arrondissement: str = ""
    region: str = ""          # département or state given in parentheses: Meurthe, Pr., Bav. ...
    xref: str = ""            # "Voy. X"
    near: str = ""            # "près de X": a lost place located near another
    numbers: list[int] = field(default_factory=list)
    numbers_raw: str = ""
    numbers_ok: bool = True
    numbers_source: str = ""  # "tesseract" when a second reading filled in garbled numbers
    note: str = ""
    last_line: tuple = ()     # (pdf page, line) holding the end of the entry, for a second reading

    @property
    def identified(self) -> bool:
        return bool(self.commune or self.canton or self.arrondissement or self.region or self.xref or self.near)

    def as_row(self) -> dict:
        return {
            "page": self.page, "name": self.name, "marker": self.marker, "kind": self.kind,
            "commune": self.commune, "canton": self.canton, "arrondissement": self.arrondissement,
            "region": self.region, "xref": self.xref, "near": self.near, "identified": int(self.identified),
            "numbers": "|".join(map(str, self.numbers)), "numbers_raw": self.numbers_raw,
            "numbers_ok": int(self.numbers_ok), "numbers_source": self.numbers_source,
            "note": self.note, "text": self.text,
        }


# The column rule of the two-column pages is sometimes read as a character before a line.
_RULE_NOISE = re.compile(r"^[{}|!ijI,:;\\/]\s+(?=\S)")
MAX_DRIFT = 15.0  # pt; the running margin may drift this far from the page's robust margin


def group_entries(lines, with_lines: bool = False) -> list:
    """Merge wrapped lines into (page, text) per entry: an entry starts at the column's left
    margin, its continuation lines are indented. `lines` holds (page record, line, cleaned text)."""
    entries: list[tuple[str, list[str], list]] = []
    margins: dict[tuple[str, bool], float] = {}  # running left margin per page column (scans are skewed)
    bases: dict[tuple[str, bool], float] = {}

    def column(rec, line) -> bool:
        return rec.page.pdf in _two_columns() and line.x0 > rec.page.width / 2 - 40

    for rec, line, _ in lines:
        text = clean.fix_circumflex(line.text.strip())
        noisy = bool(_RULE_NOISE.match(text))
        text = _RULE_NOISE.sub("", text)
        if _is_heading(text) or not re.search(r"\w", text):
            continue
        key = (rec.label, column(rec, line))
        if key not in margins:
            xs = sorted(l.x0 for r, l, _ in lines if r.label == rec.label and column(r, l) == key[1]
                        and not _is_heading(l.text.strip()) and not _RULE_NOISE.match(l.text.strip()))
            margins[key] = xs[len(xs) // 10] if xs else 0.0  # robust left margin
            bases[key] = margins[key]
        if noisy:  # its left edge is the noise: decide by the first letter
            continues = text[:1].islower() or text[:1].isdigit() or text[:1] in "(-"
        else:
            continues = line.x0 > margins[key] + CONTINUATION_INDENT or bool(re.match(r"^[\d•·]", text))
        if entries and continues:
            entries[-1][1].append(text)
            entries[-1][2].append((rec.page.pdf, line))
        else:
            entries.append((rec.label, [text], [(rec.page.pdf, line)]))
            if not noisy and abs(line.x0 - bases[key]) <= MAX_DRIFT:
                margins[key] = line.x0  # follow the drift of a skewed page
    if with_lines:
        return [(page, clean.dehyphenate(parts), src) for page, parts, src in entries]
    return [(page, clean.dehyphenate(parts)) for page, parts, _ in entries]


def _two_columns() -> range:
    return book.TWO_COLUMN_PAGES


def _is_heading(text: str) -> bool:
    return (len(text) <= 2 and text[:1].isupper()) or text.rstrip(".") in (
        "TABLE", "DES NOMS DE LIEUX", "DES FORMES ANCIENNES")


def split_fields(text: str) -> list[str]:
    """Split at commas outside parentheses."""
    fields, depth, cur = [], 0, ""
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth <= 0:
            fields.append(cur.strip())
            cur = ""
        else:
            cur += ch
    fields.append(cur.strip())
    return [f for f in fields if f]


def expand_numbers(tokens: list[str]) -> list[int]:
    """Expand abbreviated entry numbers and ranges: ["1475", "1537", "38"] -> [1475, 1537, 1538]."""
    out: list[int] = []
    prev: int | None = None
    for tok in tokens:
        a, _, b = tok.partition("-")
        start = _full(int(a), prev)
        end = _full(int(b), start, inclusive=True) if b else start
        out.extend(range(start, end + 1) if end >= start else [start])
        prev = end
    return out


def _full(n: int, prev: int | None, inclusive: bool = False) -> int:
    """`38` after 1537 is 1538; `13` after 1098 is 1113 (the next one with these last digits).
    A range's end may equal its start (`inclusive`)."""
    if prev is None or len(str(n)) >= len(str(prev)):
        return n
    width = len(str(n))
    full = int(str(prev)[: len(str(prev)) - width] + str(n).zfill(width))
    return full if full > prev or (inclusive and full == prev) else full + 10 ** width


def _is_number_field(f: str) -> bool:
    """An entry number as the OCR read it: short, one word, with a digit ("2C7", "lOuO") or tiny ("»5")."""
    f = f.strip(" .*'’")
    if not f or " " in f.replace(" -", "-").replace("- ", "-").strip():
        return False
    bits = re.split(r"-", f)
    return all(len(b) <= 5 for b in bits) and (
        sum(c.isdigit() for c in f) >= 1 or (len(f) <= 3 and bool(_NUMERIC.match(f))))


_REMARK = re.compile(r"(\d[*'’]?)\s*\.\s*\([^()]*\)\s*\.?\s*$")


def parse_entry(page: str, text: str) -> IndexEntry:
    e = IndexEntry(page, text)
    # A remark in brackets after the numbers ("1491. (C'est Sambach, ou plutôt Saubach…)") is not part of them.
    fields = split_fields(_REMARK.sub(r"\1.", normalize(text)).rstrip(" .;"))
    # Trailing entry numbers.
    tail: list[str] = []
    while len(fields) > 1 and _is_number_field(fields[-1]):
        tail.insert(0, fields.pop().strip(" ."))
    e.numbers_raw = ", ".join(tail)
    tokens = []
    for t in tail:
        fixed = "-".join(b.replace(" ", "").translate(_DIGIT) for b in re.split(r"\s*-\s*", t))
        if re.fullmatch(r"\d{1,4}(-\d{1,4})?", fixed):
            tokens.append(fixed)
        else:
            e.numbers_ok = False
    e.numbers = expand_numbers(tokens)
    if any(n < 1 or n > book.LAST_ENTRY for n in e.numbers):
        e.numbers_ok = False  # beyond the last entry: a misread digit ("2507" for 2307)
    if any(not re.fullmatch(r"[\d\s-]+", t) for t in tail):
        e.numbers_ok = False  # read through OCR confusables: to be confirmed
    # Name and note call.
    name = fields.pop(0) if fields else ""
    m = re.match(r"^(.*?[^\d\s*])\s*([\d*]{1,2})$", name)
    if m:
        name, e.marker = m.group(1), m.group(2)
    e.name = clean.fix_name(name.strip())
    if not tail and not re.search(r"\bVoy\.", text):
        e.numbers_ok = False  # every entry but a cross-reference has numbers
    # Region in parentheses at the end of the last location field.
    for i in range(len(fields) - 1, -1, -1):
        r = _REGION.search(fields[i])
        if r:
            e.region = region_name(r.group(1))
            fields[i] = fields[i][: r.start()].strip()
            break
    for f in fields:
        if not f:
            continue
        if (m := _XREF.match(f)):
            e.xref = m.group("x").strip(" .")
        elif _CHEF_LIEU.match(f):
            e.canton = e.canton or e.name
        elif (m := _COMMUNE.match(f)):
            e.commune = m.group("x").strip()
        elif (m := _CANTON.match(f)):
            e.canton = m.group("x").strip()
        elif (m := _NEAR.match(f)):
            e.near = m.group("x").strip()
            e.kind = f"{e.kind}, {f[: m.start('x')].strip()}".strip(", ") if f[: m.start('x')].strip() else e.kind
        elif (m := _ARR.match(f)):
            e.arrondissement = m.group("x").strip()
        elif (s := _STATE.search(f)):
            e.region = e.region or s.group(1)
        else:
            e.kind = f"{e.kind}, {f}" if e.kind else f
    return e


def _note_number(note: str) -> str:
    m = re.match(r"^\s*([\dIil!tSf{*]{1,2})\s?[.,]", note)
    if not m:
        return ""
    n = m.group(1)
    return n if n == "*" else n.replace("{", "1").translate(_DIGIT)


def merge_reading(e: IndexEntry, second: str) -> bool:
    """Fill in garbled entry numbers from a second reading of the entry's last line.

    A number is taken from the second reading only where it has the same length as the garbled
    one and agrees with every digit the text layer did read ("192»" accepts 1925). Returns True
    when all numbers are then clean.
    """
    raw = [t.strip() for t in e.numbers_raw.split(",")] if e.numbers_raw else []
    other = parse_entry(e.page, second)
    alt = [t.strip() for t in other.numbers_raw.split(",")] if other.numbers_raw else []
    if not raw:
        # Nothing readable in the text layer: take the second reading alone, if it is clean.
        if alt and other.numbers_ok and all(1 <= n <= book.LAST_ENTRY for n in other.numbers):
            e.numbers, e.numbers_raw = other.numbers, other.numbers_raw
            e.numbers_ok, e.numbers_source = True, "tesseract-only"
            return True
        return False
    alt = alt[-len(raw):] if raw and len(alt) >= len(raw) else alt
    if not raw or len(alt) != len(raw):
        return False
    tokens = []
    for r, a in zip(raw, alt):
        r, a = r.replace(" ", ""), a.replace(" ", "")
        if re.fullmatch(r"\d{1,4}(-\d{1,4})?", r):
            tokens.append(r)
        elif (re.fullmatch(r"\d{1,4}(-\d{1,4})?", a) and len(a) == len(r)
              and all(x == y or not x.isdigit() for x, y in zip(r, a))):
            tokens.append(a)
        else:
            return False
    numbers = expand_numbers(tokens)
    if any(n < 1 or n > book.LAST_ENTRY for n in numbers):
        return False
    e.numbers = numbers
    e.numbers_ok, e.numbers_source = True, "tesseract"
    return True


def parse_index(lines, notes_by_page: dict[str, list[str]], reread=None) -> list[IndexEntry]:
    """`reread(pdf, line)` gives a second reading of a line (Tesseract) for garbled numbers."""
    entries = []
    for page, text, src in group_entries(lines, with_lines=True):
        e = parse_entry(page, text)
        e.last_line = src[-1]
        entries.append(e)
    if reread:
        for e in entries:
            if not e.numbers_ok:
                pdf, line = e.last_line
                merge_reading(e, reread(pdf, line))
    for e in entries:
        if e.marker:
            matches = [n for n in notes_by_page.get(e.page, []) if _note_number(n) == e.marker]
            if matches:
                e.note = re.sub(r"^\s*\S{1,2}\s?[.,]\s*", "", matches[0])
    return entries


@dataclass
class OldForm:
    page: str
    old: str
    modern: str
    ok: bool
    text: str

    def as_row(self) -> dict:
        return {"page": self.page, "old": self.old, "modern": self.modern, "ok": int(self.ok), "text": self.text}


def split_old_form(text: str) -> OldForm:
    """`Abbertingen. Olberding.` -> old form and modern name; `ok` is False when unsure."""
    body = text.rstrip(" .*")
    m = (re.match(r"^(.+?)\s*\.\s*(?=[A-ZÀ-ÖØ-Ýl(])(.+)$", body)
         or re.match(r"^(.+?)\s*(?:\.[.\"'’]+|%|\.)\s*(?=\w)(.+)$", body)   # misread separators
         or re.match(r"^(.+?),\s+(.+)$", body))
    if not m:
        return OldForm("", body, "", False, text)
    old, modern = m.group(1).strip(), m.group(2).strip(" .")
    merged = bool(re.search(r"\.\s+[A-ZÀ-Ý]", modern))  # two entries read as one
    return OldForm("", clean.fix_name(old), clean.fix_name(modern), not merged, text)


def parse_old_forms(lines) -> list[OldForm]:
    """The table of old forms: two columns, already in reading order."""
    out = []
    for page, text in group_entries(lines):
        form = split_old_form(text)
        form.page = page
        out.append(form)
    return out
