"""Parse the Dénombrement (parts `denombrement` and `lists`) into territories and entries.

The text is read as blocks: an entry (a numbered line and its continuations), a section
heading (Domaine, Clergé, Fiedvez…), a territory heading, or prose. Two heading stacks, one per
hierarchy, give each entry its administrative district and its feudal realm (doc/Plan.md §2).
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from denombrement import config
from denombrement.parse import numbering
from denombrement.text import book, clean

OVERRIDES = yaml.safe_load((Path(__file__).parent / "headings.yaml").read_text())


def fold(text: str) -> str:
    """Lowercase, without accents, for matching."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", fold(text)).strip("-")
    return re.sub(r"-+", "-", s)


# --- blocks -------------------------------------------------------------------------------

@dataclass
class Block:
    kind: str                 # entry, section, heading, prose
    page: str
    lines: list[str] = field(default_factory=list)
    number: int | None = None
    token: str = ""
    cost: float = 0.0
    skipped: int = 0
    part: str = ""

    @property
    def text(self) -> str:
        return clean.dehyphenate(self.lines)


_TERMINAL = (".", ":", ";", ",")
_NOTE_CALL = re.compile(r"\s*\[\d{1,2}\]|(?<=[a-zé])[*1](?=[\s.,;:]|$)")


def blocks(lines: list[tuple[str, str, str]]) -> list[Block]:
    """Group (page, part, text) lines into blocks, reading entry numbers along the way."""
    out: list[Block] = []
    cleaned = [(page, part, _NOTE_CALL.sub("", raw).strip()) for page, part, raw in lines]
    cleaned = [(page, part, text) for page, part, text in cleaned if text]
    tokens = [numbering.leading_token(text) for _, _, text in cleaned]
    readings = numbering.assign(tokens, book.LAST_ENTRY)
    cleaned, tokens, readings = _fill_gaps(cleaned, tokens, readings)
    for (page, part, text), token, reading in zip(cleaned, tokens, readings):
        if reading:
            m = re.match(r"\s*\S*?" + re.escape(token) + r"\s?[.,^<]?\s?", text)
            body = text[m.end():].strip() if m else text
            out.append(Block("entry", page, [body], reading.number, token, round(reading.cost, 2),
                             reading.skipped, part))
            continue
        last = out[-1] if out else None
        continues = last is not None and (
            text[:1].islower() or text[:1] in "([" or last.text.endswith("-")
            or not last.text.endswith(_TERMINAL))
        if continues and not _section_of(text):
            last.lines.append(text)
        else:
            out.append(Block("prose", page, [text], part=part))
    return out


def _fill_gaps(cleaned, tokens, readings):
    """Find numbers missing between two numbered neighbours in the lines between them, also
    inside a line (two entries the OCR read as one line). Such lines are split."""
    lines = list(zip(cleaned, tokens, readings))
    numbered = [i for i, l in enumerate(lines) if l[2] is not None]
    if not numbered:
        return cleaned, tokens, readings
    # Stretches between consecutive numbered lines; the first runs from the top (after "0").
    bounds = [(-1, numbered[0])] + list(zip(numbered, numbered[1:]))
    replace: dict[int, list] = {}
    for a, b in bounds:
        low = lines[a][2].number if a >= 0 else 0
        high = lines[b][2].number
        if high - low < 2:
            continue
        want = low + 1
        candidates = range(max(a, 0), b) if a >= 0 else range(0, b)
        found_any = False
        for k in candidates:
            (page, part, text), tok, rd = replace.get(k, [lines[k]])[-1] if k in replace else lines[k]
            pos = len(tok) + 1 if k == a and tok else 0
            pieces = []
            while want < high:
                force = high - low == 2 and not found_any
                hit = numbering.find_in(text, want, pos)
                if not hit and want + 1 < high:
                    hit2 = numbering.find_in(text, want + 1, pos)
                    if hit2:
                        want, hit = want + 1, hit2  # this number is not in the text; the next one is
                if not hit and force:
                    hit = numbering.find_in(text, want, pos, force=True)
                if not hit:
                    break
                tstart, bstart, t = hit
                if want + 1 < high and numbering.cost(t, want + 1) + 0.5 <= numbering.cost(t, want):
                    want += 1  # "1514" after 1512 is 1514: 1513 is missing, not misread
                pieces.append((tstart, t, numbering.Reading(want, round(numbering.cost(t, want), 2), 0)))
                found_any = True
                pos = bstart
                want += 1
            if not pieces:
                continue
            rebuilt = []
            first = pieces[0][0]
            if text[:first].strip(" .;"):
                rebuilt.append(((page, part, text[:first].strip()), tok if first > 0 else None, rd if first > 0 else None))
            for n, (tstart, t, reading) in enumerate(pieces):
                end = pieces[n + 1][0] if n + 1 < len(pieces) else len(text)
                rebuilt.append(((page, part, text[tstart:end].strip()), t, reading))
            replace[k] = rebuilt
    out = []
    for i, l in enumerate(lines):
        out.extend(replace.get(i, [l]))
    return [l[0] for l in out], [l[1] for l in out], [l[2] for l in out]


# --- classification ---------------------------------------------------------------------

_SECTIONS = [
    ("safeguard", re.compile(r"sauvegardes?\b")),
    ("clergy", re.compile(r"\bclerg[eé]\b|^cierge\b|^villages? d[eé]pendan")),
    ("fief", re.compile(r"\bfi[ec]d[vr][ec]\S?\b|\bfi[ec]dv")),
    ("domain", re.compile(r"\bdo[mr][oa]?[a-z]?ine\b")),
]


def _section_of(text: str) -> str | None:
    """The section a heading opens, for short lines that are section headings."""
    f = fold(text)
    if len(f) > 90:
        return None
    for name, pattern in _SECTIONS:
        if pattern.search(f):
            return name
    return None


# Territory words: (pattern on folded text, territory type, hierarchy, level).
_WORDS = [
    (r"^bailliage\b", "bailiwick", "admin", 1),
    (r"\bp[rli][eé]?v[oô]s[tl][eé]", "provostship", "admin", 2),
    (r"\bo[f][fl]?[il1]c[ec]\b", "office", "admin", 2),
    (r"\b[ce][hb]as[tl][ec][lu]{1,2}a?[il]n|\bchastell?enie|\bchastelkunie", "castellany", "admin", 2),
    (r"\brecep?te\b", "receivership", "admin", 2),
    (r"^(la |les )?villes? (de|et)\b", "town_district", "admin", 2),
    (r"\bsergenterie\b", "district", "admin", 3),
    (r"(^|\s)(le |les )?bans?\b", "ban", "admin", 3),
    (r"\bmairies?\b", "mayoralty", "admin", 3),
    (r"^(la )?court de\b", "court", "admin", 3),
    (r"^(le )?val\b", "val", "admin", 3),
    (r"\bcomt[eé]\b", "county", "feudal", 2),
    (r"\bbaronn?ie\b", "barony", "feudal", 2),
    (r"\bseigneur[i1]es?\b|^(la |les )?terres?\b|\bterres? et\b", "lordship", "feudal", 2),
]
_ADMIN_RANK = ["bailiwick", "provostship", "office", "castellany", "town_district", "receivership", "val",
               "district", "court", "ban", "mayoralty", "sub_provostship", "landschultheisserei"]
_FEUDAL_RANK = ["county", "barony", "lordship", "fief", "temporality"]


@dataclass
class HeadingInfo:
    types: list[str]
    level: int
    seat: str
    pair: bool = False
    basis: str = ""
    prose: bool = False
    outside: bool = False
    section: str | None = None
    descriptor: str | None = None
    override: bool = False
    last: int | None = None      # the last entry the heading covers; the next go back to its parent


def _letters(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", fold(text))


def _override(text: str) -> dict | None:
    f = _letters(text)
    for key, value in OVERRIDES.items():
        k = _letters(key)
        if (f == k and text.rstrip().endswith(".")) if key.endswith(".") else f.startswith(k):
            return value
    return None


_GLUED = re.compile(r"(ainie|ainies|ost[ée]|ost[ée]z|eurie|euries|mairie|comt[ée])(de|d'|et|du)(?=\s|[A-ZÀ-Ý']|$)")
_SEAT_END = re.compile(r",|\s+s[cçr]av[oc]i[rt]\b|:|\s+comme dessus|\s+audict\b|\s+partie\b|\s+(?:tenu|lentiz|despendant|d[ée]pendant)\b")


def _seat(text: str, end_of_types: int) -> str:
    """The place a heading is named after: the words after its type words ("de/d'/du X")."""
    t = _GLUED.sub(r"\1 \2", text)[end_of_types:] if end_of_types else _GLUED.sub(r"\1 \2", text)
    t = _SEAT_END.split(t)[0]
    t = re.sub(r"^\s*(?:et\s+\S+\s+)*?(?:de la |des |du |de |d['’]\s*|le |la )", "", t.strip(), count=1)
    return t.strip(" .,;:")


def classify(text: str, comma_ok: bool = False) -> HeadingInfo | None:
    """What a non-entry block is: a territory heading (types, level, seat) or prose (None)."""
    ov = _override(text)
    if ov:
        return HeadingInfo(types=ov.get("types", []), level=ov.get("level", 2), seat=ov.get("seat", _seat(text, 0)),
                           pair=ov.get("pair", False), basis=ov.get("basis", ""), prose=ov.get("prose", False),
                           outside=ov.get("outside", False), section=ov.get("section"),
                           descriptor=ov.get("descriptor"), override=True, last=ov.get("last"))
    f = fold(_GLUED.sub(r"\1 \2", text))
    # A heading ends with a full stop or colon and has no verb; list items end with commas.
    if len(f) > 160 or (text.rstrip().endswith(",") and not comma_ok) or re.search(
            r"\b(est|sont|d[eé]pendent|appartien\S*|ensuivent|se tirent|se voit|souloit|meuvent)\b", f):
        return None
    found = []
    end = 0
    for pattern, ttype, hierarchy, level in _WORDS:
        m = re.search(pattern, f)
        if m and m.start() < 60:
            found.append((ttype, hierarchy, level))
            word_end = re.match(r"\S*", f[m.end():]).end()
            end = max(end, m.end() + word_end)
    if not found:
        return None
    admin = [t for t, h, _ in found if h == "admin"]
    feudal = [t for t, h, _ in found if h == "feudal"]
    types = sorted(set(admin), key=_ADMIN_RANK.index)[:1] + sorted(set(feudal), key=_FEUDAL_RANK.index)[:1]
    level = min(l for t, _, l in found if t in types)
    return HeadingInfo(types=types, level=level, seat=_seat(text, end), pair=bool(admin and feudal),
                       basis="heading" if admin and feudal else "")


# --- canonical seat names ---------------------------------------------------------------------

class Gazetteer:
    """Modern names for the book's spellings: the table of old forms, then the index."""

    def __init__(self, raw_dir: Path = config.RAW_DIR):
        self.old: dict[str, str] = {}
        self.modern: dict[str, str] = {}
        if (raw_dir / "old_forms.csv").exists():
            for r in csv.DictReader((raw_dir / "old_forms.csv").open()):
                if r["ok"] == "1" and r["modern"]:
                    self.old.setdefault(_letters(r["old"]), re.sub(r"\s*\(.*?\)", "", r["modern"]).strip())
        if (raw_dir / "index.csv").exists():
            for r in csv.DictReader((raw_dir / "index.csv").open()):
                name = re.sub(r"\s*\(.*?\)|[*\d]+$", "", r["name"]).strip()
                if name:
                    self.modern.setdefault(_letters(name), name)

    def modern_name(self, seat: str) -> str:
        """The modern name of a seat, part by part ("Mirccourt et Reuioneourt")."""
        parts = re.split(r"\s+et\s+", seat)
        return " et ".join(self._one(p) for p in parts)

    @staticmethod
    def _loose(key: str) -> str:
        """The key with the scan's usual letter confusions made equal (c/e, l/t)."""
        return key.translate(str.maketrans("ct", "el"))

    def _one(self, name: str) -> str:
        key = _letters(clean.fix_name(name))
        if not key:
            return name
        for table in (self.old, self.modern):
            if key in table:
                return table[key]
        for table in (self.modern, self.old):  # "Einvilte" and the index's "Einvillc" are Einville
            loose = {self._loose(k): v for k, v in table.items()}
            if self._loose(key) in loose:
                return loose[self._loose(key)]
        # Near matches: the index's modern names first (the old-forms table maps some spellings to
        # other places of the same name: "Einville. Euville.").
        if len(key) >= 7:  # short names have too many near neighbours
            for table in (self.modern, self.old):
                same_initial = [k for k in table if k[:1] == key[:1]]
                hit = difflib.get_close_matches(key, same_initial, n=1, cutoff=0.85)
                if hit:
                    return table[hit[0]]
        return clean.fix_name(name)


# --- territories and entries -----------------------------------------------------------------

@dataclass
class Territory:
    key: str
    type: str
    hierarchy: str
    seat: str
    level: int
    page: str
    heading: str
    seat_as_printed: str = ""
    parent: str | None = None        # admin parent, or feudal parent of a realm
    ressort: str | None = None       # the division a realm answers to
    counterpart: str | None = None
    basis: str = ""
    holder_text: str = ""            # "les sieurs comtes d'Eberstein et Oberstein"
    notes: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


@dataclass
class Entry:
    no: int
    page: str
    token: str
    cost: float
    text: str
    name: str
    descriptors: list[str]
    district: str | None
    realm: str | None
    section: str
    series: str
    order: str | None = None
    share: str | None = None
    share_text: str = ""
    holder_text: str = ""
    flags: list[str] = field(default_factory=list)


_DESCRIPTORS = [
    ("castle", r"\b[ce][hb]as[tl]eaux?\b|\bchasteau|\bmaison forte"),
    ("town", r"\bvilles?\b(?! de)"),
    ("small_town", r"\bbourgs?\b"),
    ("village", r"\bvillages?\b"),
    ("hamlet", r"\bhameau"),
    ("abbey", r"\babba[iy]e"),
    ("priory", r"\bprieur[eé]"),
    ("collegiate_church", r"coll[eé]gia"),
    ("convent", r"\bcouvent|\bmonast[eè]re"),
    ("commandery", r"\bcommanderie"),
    ("hospital", r"\bhospital|\bh[oô]pital"),
    ("farmstead", r"\bcen[sc]e\b"),
    ("grange", r"\bgagnage"),
    ("glassworks", r"\bverrerie"),
    ("saltworks", r"\bsalines?\b"),
    ("mill", r"\bmoulin"),
    ("mine", r"\bm[iy]nes?\b"),
    ("market", r"\bmarch[eé]\b"),
    ("passage", r"\bpassage"),
    ("pleasure_house", r"maison de plaisir"),
    ("palace", r"\bpalais\b"),
    ("deserted_village", r"\bruin[eé]|\bruyn[eé]|\bdestruict"),
]
_ORDERS = [
    ("benedictine", r"sainct\s*be[nm]oi|saint\s*beno|benoist|benedict"),
    ("cistercian", r"cist[eé]?aux?|citeaux|cisteau"),
    ("premonstratensian", r"pr[eé]mon?str"),
    ("augustinian", r"augustin|chanoines? r[eé]gulier"),
    ("cluniac", r"\bcluny"),
    ("carthusian", r"chartreu"),
    ("poor_clares", r"\bclar[ei]|saincte[- ]claire"),
    ("franciscan", r"cordelier|sainct[- ]fran[cç]ois|observance"),
    ("dominican", r"prescheu|prescheresse|dominic"),
    ("minim", r"\bminimes?\b"),
    ("capuchin", r"capuc"),
    ("jesuit", r"j[eé]su[iy]t"),
    ("antonine", r"sainct[- ]anthoine|antonin"),
    ("hospitaller", r"sainct[- ]jean de h|hi[eé]rusalem|malte"),
    ("teutonic", r"teuton"),
]
_SERIES = [  # headings of the thematic lists after the Dénombrement
    ("towns", r"^noms des villes"),
    ("cathedrals", r"^eglises? cath[eé]drale"),
    ("collegiates", r"^eglises? coll[eé]gia"),
    ("abbeys_m", r"^abbayes de religieux"),
    ("abbeys_f", r"^abbayes de dames"),
    ("convents_f", r"^couven\S* de religieuses"),
    ("grey_sisters", r"^s[oœ]e?urs grises"),
    ("other_sisters", r"^autres s[oœ]e?urs"),
    ("priories", r"^prieur"),
    ("friaries", r"^couven\S* de cordelier"),
    ("convents_m", r"^couven\S* d'autres religieux"),
    ("commanderies", r"^c[o0]r?n?m+anderies"),
    ("charterhouses", r"chartreuse"),
]


def entry_name(text: str) -> str:
    name = re.split(r",|\s+\(|\.\s*$", text, maxsplit=1)[0].strip(" .")
    return clean.fix_name(name)


def descriptors(text: str) -> list[str]:
    rest = fold(text.split(",", 1)[1]) if "," in text else ""
    return [key for key, pattern in _DESCRIPTORS if re.search(pattern, rest)]


def order_of(text: str) -> str | None:
    f = fold(text)
    for key, pattern in _ORDERS:
        if re.search(pattern, f):
            return key
    return None


def share_of(text: str) -> tuple[str | None, str]:
    f = fold(text)
    m = re.search(r"pour (la|une) moi[c]?ti[eé]|par moi[c]?ti[eé]|moi[c]?ti[eé] (a|au)", f)
    if m:
        return "1/2", text[m.start():].strip(" .")
    m = re.search(r"\b(en |pour une |pour )?partie\b", f)
    if m:
        return "part", text[m.start():].strip(" .")
    return None, ""


_HOLDER = re.compile(r"(?:tenu[sz]?|lentiz|tenir) en fi[ec]d.*?\bpar\s+(?P<a>.+)$|tenir en fi[ec]d\S* d\S+ .*? (?P<b>les seigneur.+)$", re.I)


@dataclass
class Parse:
    territories: dict[str, Territory] = field(default_factory=dict)
    entries: list[Entry] = field(default_factory=list)
    prose: list[dict] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def _in(seat_slug: str, names: set[str]) -> bool:
    """Whether a seat is one of the names a sentence listed (both OCR'd: compared loosely)."""
    return seat_slug in names or bool(difflib.get_close_matches(seat_slug, list(names), n=1, cutoff=0.7))


def parse(lines: list[tuple[str, str, str]], gazetteer: Gazetteer | None = None) -> Parse:
    out = Parse()
    gazetteer = gazetteer or Gazetteer()
    duchy = Territory("duchy-lorraine", "duchy", "admin", "Lorraine", 0, "34", "Duché de Lorraine")
    out.territories[duchy.key] = duchy
    admin: list[Territory] = [duchy]     # stack: duchy, bailiwick, district, sub-district
    realm: Territory | None = None       # the open feudal realm
    section: str | None = None
    series = "main"
    descriptor_hint: str | None = None
    listed: set[str] = set()             # the level-2 seats a bailliage's opening sentence names
    dependents: dict[str, set[str]] = {}  # division key -> the realms said to depend on it
    collecting: str | None = None        # "listed" or a division key, while a list sentence goes on
    outside = False
    realm_before: Territory | None = None  # the realm an abbey's lands interrupt
    ends: dict[str, int] = {}            # division key -> the last entry its heading covers (headings.yaml `last`)

    def add(t: Territory) -> Territory:
        if t.key in out.territories:      # "Ban d'Uxegney, comme dessus": the same territory again
            return out.territories[t.key]
        out.territories[t.key] = t
        return t

    def district_parent(level: int) -> Territory:
        for t in reversed(admin):
            if t.level < level:
                return t
        return duchy

    all_blocks = blocks(lines)
    for i, b in enumerate(all_blocks):
        next_is_entry = i + 1 < len(all_blocks) and all_blocks[i + 1].kind == "entry"
        if b.kind == "entry":
            collecting = None
            if b.number > 2290 and series == "main" and b.part == "lists":
                series = "towns"
            text = b.text
            share, share_text = share_of(text)
            e = Entry(
                no=b.number, page=b.page, token=b.token, cost=b.cost, text=text, name=entry_name(text),
                descriptors=descriptors(text) + ([descriptor_hint] if descriptor_hint else []),
                district=admin[-1].key if series == "main" and len(admin) > 1 else None,
                realm=realm.key if series == "main" and realm else None,
                section=section or ("other" if series == "main" else ""),
                series=series, order=order_of(text) if re.search(r"ordre|abba|prieur|couvent|cordelier|j[eé]su", fold(text)) or series != "main" else None,
                share=share, share_text=share_text)
            if series == "main" and section is None:
                e.flags.append("no section heading: section inferred as other")
            if b.skipped:
                e.flags.append(f"{b.skipped} number(s) missing before")
            if b.cost >= 1.0:
                e.flags.append(f"number read from '{b.token}'")
            out.entries.append(e)
            if admin[-1].key in ends and b.number == ends[admin[-1].key]:
                # "La Court de Perle, sçavoir : Oberperl, Niderperl et Syndorff": the list that follows
                # is the prévôté's again.
                admin = admin[:-1]
            m = re.search(r"abba\S*\s+(?:dudict |de |d')\s*(?P<x>[^,]+),.*de laquelle d[eé]pendent les villages", text)
            if series == "main" and m:
                # "L'abbaye dudict Sainct-Avol, …, de laquelle dépendent les villages cy-après":
                # the entries that follow are the abbey's lands.
                seat = gazetteer.modern_name(m.group("x").strip())
                realm_before = realm
                realm = add(Territory(f"temporality-abbey-{slug(seat)}", "temporality", "feudal", seat, 3, b.page,
                                      text, ressort=[a for a in admin if a.level <= 2][-1].key))
            continue

        text = b.text
        f = fold(text)
        # Thematic lists.
        if b.part == "lists":
            for key, pattern in _SERIES:
                if re.search(pattern, f):
                    series = key
                    break
            else:
                out.prose.append({"page": b.page, "text": text, "context": series})
            continue
        sec = _section_of(text)
        info = classify(text, comma_ok=next_is_entry)
        if info and info.prose:
            if info.section:
                section = info.section
            descriptor_hint = info.descriptor
            out.prose.append({"page": b.page, "text": text, "context": admin[-1].key})
            continue
        if info and info.outside:
            outside, listed = True, set()
            admin, realm, section = [duchy], None, None
            out.prose.append({"page": b.page, "text": text, "context": "outside the bailliages"})
            continue
        if sec and (not info or len(f) < 40 or "clerg" in f or "sauvegard" in f):
            section = sec
            if realm is not None and realm.type == "temporality":
                realm = realm_before  # an abbey's lands end with their section
            if re.search(r"\bpour (le clerg|les fi)", f) and not f.startswith("pour"):
                # "Sainct-Diey et Raon pour le clergé": the section covers the whole prévôté.
                admin = [t for t in admin if t.level <= 2]
                realm = None
            descriptor_hint = info.descriptor if info else None
            if sec == "clergy" and re.search(r"villages? d[eé]pendan\S* de l.abbaye", f):
                # "Villages dépendants de l'abbaye de Longeville …": the abbey's lands.
                seat = re.sub(r",.*$", "", re.split(r"abbaye d[e']\s*", text, maxsplit=1)[-1]).strip(" .")
                seat = gazetteer.modern_name(seat)
                t = add(Territory(f"temporality-abbey-{slug(seat)}", "temporality", "feudal", seat, 3, b.page,
                                  text, ressort=[a for a in admin if a.level <= 2][-1].key))
                realm_before, realm = realm, t
            continue
        if not info or (text.rstrip().endswith(",") and not next_is_entry):
            out.prose.append({"page": b.page, "text": text, "context": admin[-1].key})
            # A bailliage's opening sentence lists its prévôtés; "… de laquelle … dépendent les terres
            # et seigneuries qui ensuivent" lists the realms answering to a prévôté.
            m = re.search(r"pr[eé]vost\S* et \S+ de ([A-ZÀ-Ý][\w'-]+), de laquelle.*d[eé]pendent", text)
            if m:
                collecting = f"provostship-{slug(gazetteer.modern_name(m.group(1)))}"
                dependents.setdefault(collecting, set())
            elif re.search(r"soubz? (ce|ledict) bailliage|^item, les pr", f):
                collecting = "listed"
            if collecting and (len(f) < 40 or "qui ensuivent" in f or "soubz" in f or "item" in f):
                names = re.sub(r"^.*?(?:ensuivent,? s[cç]avoir\s*:|\b(?:de|d')\s+(?=[A-ZÉ]))", "", text)
                if re.match(r"^(le |la |les |terres? |du |de )", fold(text)):
                    names = re.sub(r"^(?:Le |La |Les |Terres? |Du |De |de )+(?:comt[eé] de |de |d')?", "", text)
                for name in re.split(r",|\bet\b|:|\bpour\b.*$", names):
                    name = re.sub(r"^(?:de |du |d')", "", name.strip(" .;"))
                    if name and len(name) < 30:
                        target = listed if collecting == "listed" else dependents[collecting]
                        target.add(slug(gazetteer.modern_name(name)))
            if len(f) >= 40 and not re.search(r"qui ensuivent|soubz|item|s[cç]avoir\s*:$|:$", f):
                collecting = None  # a sentence that isn't the list
            continue

        # A territory heading.
        collecting = None
        admin_types = [t for t in info.types if t in _ADMIN_RANK]
        feudal_types = [t for t in info.types if t in _FEUDAL_RANK]
        printed_seat = info.seat
        if not info.override:
            info.seat = gazetteer.modern_name(info.seat)
        seat_slug = slug(info.seat)
        level = info.level
        if outside and level == 3 and not info.override and set(info.types) & {
                "val", "lordship", "county", "town_district", "castellany", "provostship"}:
            level = 2  # outside the bailliages, towns, vals and terres stand directly under the duchy
        dependent_of = next((d for d, names in dependents.items() if _in(seat_slug, names)), None)
        in_slot = bool(feudal_types) and not admin_types and not dependent_of and (
            _in(seat_slug, listed) or (outside and level <= 2) or level == 1)
        holder = _HOLDER.search(text)
        holder_text = (holder.group("a") or holder.group("b") or "").strip(" .") if holder else ""
        if feudal_types and not admin_types and not in_slot and (len(admin) >= 3 or dependent_of):
            # A realm inside a district (Terre de Pierrefort in the prévôté of Nancy): it answers to
            # the prévôté, whose entries follow again after the realm's.
            admin = [t for t in admin if t.level <= 2]
            parent_realm = realm if realm and realm.counterpart else None
            t = add(Territory(f"{feudal_types[0]}-{seat_slug}", feudal_types[0], "feudal", info.seat, 3, b.page, text,
                              parent=parent_realm.key if parent_realm else None,
                              ressort=dependent_of or admin[-1].key,
                              seat_as_printed=printed_seat, holder_text=holder_text))
            realm = t
            descriptor_hint = None
            continue
        # An administrative division (with its realm when the heading or the slot says so).
        if not admin_types:
            admin_types = ["district"]
            basis = "slot" if _in(seat_slug, listed) or outside else (info.basis or "slot")
            if level >= 2 and not in_slot:
                d_flag = "a realm heading directly under a bailliage, not in its list of prévôtés"
            else:
                d_flag = ""
        else:
            basis, d_flag = info.basis, ""
        if level == 1:
            admin, realm, section, listed, outside = [duchy], None, None, set(), False
            collecting = None
        parent = district_parent(level)
        if outside and level == 2:
            parent = duchy
        d = add(Territory(f"{admin_types[0]}-{seat_slug}", admin_types[0], "admin", info.seat, level, b.page, text,
                          parent=parent.key, seat_as_printed=printed_seat))
        if d_flag:
            d.flags.append(d_flag)
        admin = [t for t in admin if t.level < level] + [d]
        if info.last:
            ends[d.key] = info.last
            d.notes.append(f"its heading covers entries up to {info.last} (headings.yaml)")
        if level <= 2:
            section = None
            realm = None
        elif realm and not (realm.counterpart and realm.counterpart in [t.key for t in admin]):
            realm = None
        if feudal_types:
            r = add(Territory(f"{feudal_types[0]}-{seat_slug}", feudal_types[0], "feudal", info.seat, level, b.page,
                              text, ressort=d.key, counterpart=d.key, basis=basis, seat_as_printed=printed_seat,
                              holder_text=holder_text))
            d.counterpart, d.basis = r.key, basis
            realm = r
        descriptor_hint = None
    _check_sequence(out)
    return out


def _check_sequence(out: Parse) -> None:
    numbers = [e.no for e in out.entries]
    missing = sorted(set(range(1, book.LAST_ENTRY + 1)) - set(numbers))
    if missing:
        out.issues.append(f"{len(missing)} numbers missing: {missing[:40]}")
    dupes = sorted({n for n in numbers if numbers.count(n) > 1})
    if dupes:
        out.issues.append(f"duplicate numbers: {dupes}")


def read_lines() -> list[tuple[str, str, str]]:
    lines = []
    with (config.RAW_DIR / "pages.jsonl").open() as f:
        for raw in f:
            page = json.loads(raw)
            for line in page["body"]:
                if line["part"] in ("denombrement", "lists"):
                    lines.append((page["printed"], line["part"], line["clean"]))
    return lines


def run() -> Parse:
    result = parse(read_lines())
    out_dir = config.EXTRACTED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "entries.jsonl").open("w") as f:
        for e in result.entries:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
    with (out_dir / "territories.jsonl").open("w") as f:
        for t in result.territories.values():
            f.write(json.dumps(asdict(t), ensure_ascii=False) + "\n")
    with (out_dir / "prose.jsonl").open("w") as f:
        for p in result.prose:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    return result
