"""Stage 4: build data/curated/*.csv from the parse (data/extracted/), the index (data/raw/),
hand-entered rows (data/curated/manual/) and review decisions (data/curated/rules.yaml).

Never edit the generated tables: hand fixes go into `manual/` or `rules.yaml`, and
`make curate` can always be re-run.
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from denombrement import config
from denombrement.curate import corrections, reconcile
from denombrement.data import models
from denombrement.data.store import load_vocab
from denombrement.parse import numbering
from denombrement.text import clean

REVIEW_DIR = config.DATA_DIR / "review"
DUKE = "duchy-lorraine"

# Digit pairs the OCR confuses; an index number is checked against these variants too.
_CONFUSED = [("3", "5"), ("1", "4"), ("1", "7"), ("5", "6"), ("6", "8"), ("3", "8"), ("0", "6"), ("0", "9"), ("0", "5")]


# --- names ------------------------------------------------------------------------------------

def fold(text: str) -> str:
    # œ and æ have no decomposition: "Hœlling" is hoelling, not h-lling
    t = unicodedata.normalize("NFKD", text.replace("œ", "oe").replace("Œ", "Oe").replace("æ", "ae").replace("Æ", "Ae"))
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", fold(text))).strip("-")


def display_name(name: str) -> str:
    """The index's "Malgrange (la)" as "La Malgrange"; note calls and remarks in brackets
    ("Oberkirchen* (anciennement Catharin-Ostern)") left out."""
    name = re.sub(r"[*\d]+(?=\s|$|\()", "", name).strip(" ,.")
    m = re.match(r"^(.*?)\s*[({]\s*(la|le|les|l')\s*[)}]\s*$", name, re.I)
    if m:
        article = m.group(2).capitalize()
        name = f"{article}{'' if article.endswith(chr(39)) else ' '}{m.group(1)}"
    else:
        name = re.sub(r"\s*[({][^)}]*[)}]?\s*$", "", name).strip(" ,.") or name
    return clean.fix_name(name)


def name_key(name: str) -> str:
    """For comparing an old spelling with a modern name: no article, "Sainct" = "Saint",
    the scan's c/e and l/t confusions made equal."""
    f = fold(name)
    f = re.sub(r"\((?:la|le|les|l')\)|^(?:la|le|les|l')\s+|^l'", "", f)
    f = f.replace("sainct", "saint").replace("ssweiller", "sweiler").replace("weiller", "weiler")
    f = re.sub(r"[^a-z]", "", f)
    return f.translate(str.maketrans("ct", "el"))


_SUFFIX = re.compile(r"[- ](?:sur|sous|les|lès|lez|en|devant|aux|au|la|le|de|du|des|d'|haut|bas|basse|haute|grand|petit)[- ].*$", re.I)


def similarity(a: str, b: str) -> float:
    """How alike an old spelling and a modern name are; "Charmes" is "Charmes-sur-Moselle"."""
    ka = name_key(a)
    best = 0.0
    for name in {b, _SUFFIX.sub("", b)}:
        kb = name_key(name)
        if ka and kb:
            best = max(best, difflib.SequenceMatcher(None, ka, kb).ratio())
    return best


def variants_of(n: int) -> set[int]:
    """Numbers the OCR could have printed for `n` (one confused digit)."""
    s = str(n)
    out = set()
    for i, d in enumerate(s):
        for a, b in _CONFUSED:
            for x, y in ((a, b), (b, a)):
                if d == x:
                    v = s[:i] + y + s[i + 1:]
                    if not v.startswith("0"):
                        out.add(int(v))
    out.discard(n)
    return out


# --- inputs ---------------------------------------------------------------------------------

def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def load_rules() -> dict:
    path = config.CURATED_DIR / "rules.yaml"
    return yaml.safe_load(path.read_text()) or {} if path.exists() else {}


def load_manual(table: str) -> list[dict]:
    path = config.CURATED_DIR / "manual" / f"{table}.csv"
    return list(csv.DictReader(path.open())) if path.exists() else []


# --- matching entries to the index ------------------------------------------------------------

@dataclass
class Match:
    row: corrections.IndexRow | None
    how: str          # number, number+name, confused number, name, rule, none
    sim: float
    confidence: str


class Matcher:
    def __init__(self, rows: list[corrections.IndexRow], old_forms: list[dict]):
        self.rows = [r for r in rows if not r.deleted and not r.entry.xref]
        self.by_number: dict[int, list[corrections.IndexRow]] = defaultdict(list)
        for r in self.rows:
            for n in r.entry.numbers:
                self.by_number[n].append(r)
        # old spelling -> modern names (the editor's table of old forms)
        self.old: dict[str, set[str]] = defaultdict(set)
        for f in old_forms:
            if f.get("ok") == "1" and f["modern"]:
                self.old[name_key(f["old"])].add(name_key(re.sub(r"\(.*?\)", "", f["modern"])))

    def sim(self, entry_name: str, row: corrections.IndexRow) -> float:
        s = similarity(entry_name, row.entry.name)
        # The table of old forms bridges spellings that look nothing alike ("Marchainville").
        k = name_key(entry_name)
        if k in self.old and any(difflib.SequenceMatcher(None, m, name_key(row.entry.name)).ratio() > 0.85
                                 for m in self.old[k]):
            s = max(s, 0.95)
        return s

    def by_name(self, name: str) -> tuple[float, corrections.IndexRow] | None:
        if len(name_key(name)) < 5:
            return None
        best = max(self.rows, key=lambda r: self.sim(name, r))
        return self.sim(name, best), best

    def match(self, no: int, name: str) -> Match:
        exact = self.by_number.get(no, [])
        confused = [r for v in variants_of(no) for r in self.by_number.get(v, []) if r not in exact]
        scored = [(self.sim(name, r), "number", r) for r in exact] + [(self.sim(name, r), "confused", r) for r in confused]
        best_exact = max((s for s in scored if s[1] == "number"), default=None, key=lambda s: s[0])
        best_conf = max((s for s in scored if s[1] == "confused"), default=None, key=lambda s: s[0])
        # A confused number wins only when its name fits clearly better (the index misread a digit).
        if best_conf and best_conf[0] >= 0.75 and (not best_exact or best_conf[0] >= best_exact[0] + 0.3):
            return Match(best_conf[2], "confused number", best_conf[0], "medium")
        if best_exact and best_exact[0] < 0.4:
            # The number points at a line whose name doesn't fit: is there one that does?
            by_name = self.by_name(name)
            if by_name and by_name[0] >= 0.9:
                return Match(by_name[1], "name", by_name[0], "medium")
        if best_exact:
            s, _, row = best_exact
            if s >= 0.5:
                return Match(row, "number+name", s, "high")
            if len(exact) == 1 and s >= 0.25:
                return Match(row, "number", s, "medium")  # the editor's identification; old and new names differ
        if best_conf and best_conf[0] >= 0.8:
            return Match(best_conf[2], "confused number", best_conf[0], "medium")
        # A line whose number reads loosely as this one, or whose numbers are garbled, when the names agree.
        loose = [(self.sim(name, r), r) for r in self.rows
                 if (not r.entry.numbers_ok or any(numbering.cost(str(m), no) <= 1.0 for m in r.entry.numbers))
                 and r not in exact]
        loose = [x for x in loose if x[0] >= 0.82]
        if loose:
            s, row = max(loose, key=lambda x: x[0])
            return Match(row, "loose number", s, "medium")
        # Last: the name alone, among all rows.
        by_name = self.by_name(name)
        if by_name and by_name[0] >= 0.9:
            return Match(by_name[1], "name", by_name[0], "low")
        return Match(None, "none", 0.0, "low")


# --- building ---------------------------------------------------------------------------------

@dataclass
class Built:
    entries: list[dict] = field(default_factory=list)
    places: dict[str, dict] = field(default_factory=dict)
    memberships: list[dict] = field(default_factory=list)
    entities: dict[str, dict] = field(default_factory=dict)
    holdings: list[dict] = field(default_factory=list)
    features: list[dict] = field(default_factory=list)
    report: list[str] = field(default_factory=list)
    entries_raw: list[dict] = field(default_factory=list)
    index_links: list[dict] = field(default_factory=list)
    resolution: reconcile.Resolution | None = None


def _country(region: str) -> str | None:
    if region in ("Pr.", "Bav.") or "Oldenbourg" in region or "Oldenburg" in region:
        return "DE"
    if region == "Luxembourg":
        return "LU"
    return "FR"


def _place_type(index_kind: str, descriptors: list[str]) -> str:
    k = fold(index_kind)
    d = set(descriptors)
    for key, pattern in (("deserted_village", r"detr|detruit"), ("hamlet", r"^ham|\bham\."), ("farmstead", r"\bcen[sc]e|ferme"),
                         ("mill", r"moulin"), ("glassworks", r"verrerie"), ("grange", r"gagnage"), ("abbey", r"^anc\. abbaye|^abbaye"),
                         ("priory", r"^anc\. prieur|^prieur")):
        if re.search(pattern, k):
            return key
    for key in ("town", "small_town"):
        if key in d:
            return key
    if d & {"castle"} and not d & {"village", "town", "small_town"}:
        return "castle"
    if "abbey" in d and not d & {"village", "town"}:
        return "abbey"
    if "priory" in d and not d & {"village", "town"}:
        return "priory"
    if "glassworks" in d:
        return "glassworks"
    return "village"


def _territory_names(ttype: str, seat: str, vocab: dict) -> tuple[str, str, str]:
    if ttype == "temporality":
        return (f"Temporel de l'abbaye de {seat}", f"Kirchengut der Abtei {seat}", f"Lands of the abbey of {seat}")
    labels = vocab["territory_types"][ttype]
    fr = labels["fr"][0].upper() + labels["fr"][1:]
    de_ = "d'" if fold(seat)[:1] in "aeiouyh" else "de "
    de = re.sub(r"\s*\(.*\)$", "", labels["de"])   # "Bellistum (Oberamt)" names "Bellistum Nancy", as in hist_map
    return (f"{fr} {de_}{seat}", f"{de} {seat}", f"{labels['en'][0].upper() + labels['en'][1:]} of {seat}")


def build() -> Built:
    out = Built()
    vocab = load_vocab(config.CURATED_DIR / "vocab.yaml")
    rules = load_rules()
    rows = corrections.load_index()
    old_forms = corrections.load_old_forms()
    corr_log = corrections.apply(rows, old_forms)
    commune_fixes = _canonical_seats(rows)
    matcher = Matcher(rows, old_forms)
    # The index names the département or state on some lines of a canton only: carry it over.
    canton_region: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if r.entry.region and r.entry.canton:
            canton_region[name_key(r.entry.canton)][r.entry.region] += 1
    for r in rows:
        if not r.entry.region and r.entry.canton and canton_region.get(name_key(r.entry.canton)):
            r.entry.region = canton_region[name_key(r.entry.canton)].most_common(1)[0][0]
    entries = split_entries(read_jsonl(config.EXTRACTED_DIR / "entries.jsonl"), rules)
    territories = read_jsonl(config.EXTRACTED_DIR / "territories.jsonl")

    # --- territories (renamed by rules where the OCR garbled the seat) ---
    renames = {k: v for k, v in (rules.get("territory_seats") or {}).items()}
    key_map: dict[str, str] = {}
    for t in territories:
        seat = renames.get(t["key"], t["seat"])
        prefix = "temporality-abbey" if t["type"] == "temporality" else slug(t["type"])
        key_map[t["key"]] = t["key"] if t["key"] == DUKE else f"{prefix}-{slug(seat)}"
        t["seat"] = seat
    for t in territories:
        key = key_map[t["key"]]
        fr, de, en = _territory_names(t["type"], t["seat"], vocab) if key != DUKE else (
            "Duché de Lorraine", "Herzogtum Lothringen", "Duchy of Lorraine")
        out.places[key] = {
            "id": key, "kind": "territory", "name_fr": fr, "name_de": de, "name_en": en,
            "variants": t.get("seat_as_printed", "") if t.get("seat_as_printed") and t.get("seat_as_printed") != t["seat"] else "",
            "place_type": t["type"], "hierarchy": t["hierarchy"], "holder_id": "",
            "counterpart_id": key_map.get(t["counterpart"], "") if t.get("counterpart") else "",
            "counterpart_basis": t.get("basis", "") if t.get("counterpart") else "",
            "source_page": t["page"], "confidence": "high" if not t["flags"] else "medium",
            "notes": "; ".join(t["flags"]),
        }
        if t.get("parent"):
            rel = "feudal" if t["hierarchy"] == "feudal" else "admin"
            out.memberships.append({"child_id": key, "parent_id": key_map[t["parent"]], "relation": rel, "share": "",
                                    "source_page": t["page"]})
        if t.get("ressort"):
            out.memberships.append({"child_id": key, "parent_id": key_map[t["ressort"]], "relation": "ressort",
                                    "share": "", "source_page": t["page"]})

    # rules.yaml territory_names: names a territory has in use, not "<type> of <seat>" ("Deutsches Bellistum")
    for key, names in (rules.get("territory_names") or {}).items():
        if key not in out.places:
            raise ValueError(f"rules.yaml territory_names: no territory {key}")
        for lang in ("fr", "de", "en"):
            if names.get(lang):
                out.places[key][f"name_{lang}"] = names[lang]

    # --- entities and realm holders ---
    out.entities[DUKE] = {"id": DUKE, "name_en": "Duke of Lorraine", "name_fr": "Duc de Lorraine",
                          "name_de": "Herzog von Lothringen", "entity_type": "duchy", "source_page": "35",
                          "notes": '"Vostre Altesse", "Son Altesse": Charles III in 1594.'}
    for e in load_manual("entities"):
        out.entities[e["id"]] = {k: v for k, v in e.items() if k in models.Entity.model_fields}
    for t in territories:
        if t["type"] == "temporality":
            key = key_map[t["key"]]
            abbey = "abbey-" + key.removeprefix("temporality-abbey-")
            out.entities.setdefault(abbey, {
                "id": abbey, "name_en": f"Abbey of {t['seat']}", "name_fr": f"Abbaye de {t['seat']}",
                "name_de": f"Abtei {t['seat']}", "entity_type": "abbey", "source_page": t["page"]})
            out.places[key]["holder_id"] = abbey
    holders = {key_map.get(k, k): v for k, v in (rules.get("realm_holders") or {}).items()}
    unresolved_holders = []
    for key, p in out.places.items():
        if p["hierarchy"] != "feudal":
            continue
        if key in holders:
            ids = holders[key] if isinstance(holders[key], list) else [holders[key]]
            p["holder_id"] = "|".join(ids)
        t = next((t for t in territories if key_map[t["key"]] == key), None)
        if t and t.get("holder_text") and key not in holders:
            unresolved_holders.append(f"- `{key}`: \"{t['holder_text']}\"")

    def realm_holders(realm: str | None) -> list[str]:
        if not realm or realm not in out.places:
            return []
        return [h for h in out.places[realm]["holder_id"].split("|") if h]

    # --- entries and their places ---
    entry_places = {int(k): v for k, v in (rules.get("entry_places") or {}).items()}
    for no, name in (rules.get("entry_names") or {}).items():
        for e in entries:
            if e["no"] == int(no):
                e["name"] = name
    row_ids: dict[int, str] = {}
    used_ids: set[str] = set(out.places)
    matches: dict[int, Match] = {}
    entry_index = {int(k): v for k, v in (rules.get("entry_index") or {}).items()}
    for e in entries:
        if e["no"] in entry_places:
            matches[e["no"]] = Match(None, "rule", 1.0, "high")
            continue
        if e["no"] in entry_index:
            # The index line named in rules.yaml, for a match the numbers got wrong.
            want = name_key(entry_index[e["no"]])
            row = next((r for r in matcher.rows if name_key(r.entry.name) == want), None)
            if row is None:
                raise ValueError(f"rules.yaml entry_index {e['no']}: no index line '{entry_index[e['no']]}'")
            matches[e["no"]] = Match(row, "rule", 1.0, "high")
            continue
        matches[e["no"]] = matcher.match(e["no"], e["name"])

    # Every number of every index line, resolved to the entry it means (curate/reconcile.py). An
    # entry the matcher left alone takes the line whose number names it.
    resolution = reconcile.resolve(matcher.rows, entries, matches, matcher.sim, similarity)
    for no, links in resolution.by_entry().items():
        unmatched = matches[no].row is None and matches[no].how == "none"
        # …and so does one whose line no longer claims it (a correction or a decision by hand)
        dropped = matches[no].row is not None and all(x.row is not matches[no].row for x in links)
        if unmatched or dropped:
            best = max(links, key=lambda x: (x.status == "manual", x.sim))
            matches[no] = Match(best.row, "index number", best.sim, "medium")

    def place_for_row(row: corrections.IndexRow, e: dict, m: Match | None) -> str:
        rid = id(row)
        if rid in row_ids:
            return row_ids[rid]
        ie = row.entry
        name = display_name(ie.name)
        pid = slug(name)
        if pid in used_ids:
            pid = f"{pid}-{slug(ie.canton or ie.commune or ie.region or row.page)}"
        while pid in used_ids:
            pid += "-2"
        used_ids.add(pid)
        row_ids[rid] = pid
        out.places[pid] = {
            "id": pid, "kind": "settlement", "name_fr": name, "name_de": "", "name_en": "", "variants": "",
            "place_type": _place_type(ie.kind, e["descriptors"]), "modern_country": _country(ie.region),
            "index_kind": ie.kind, "index_commune": ie.commune, "index_canton": ie.canton or ie.near,
            "index_dept": ie.region, "lost": "true" if not ie.identified else "",
            "source_page": e["page"], "confidence": "high", "notes": "; ".join(row.corrected),
        }
        return pid

    # A thematic-list entry whose match is weak takes the place of the Dénombrement entry of the
    # same name ("Charmes" in the list of towns is the Charmes of entry 869).
    main_by_key: dict[str, dict] = {}
    for e in entries:
        if e["series"] == "main":
            main_by_key.setdefault(name_key(e["name"]), e)
    list_links: dict[int, int] = {}
    for e in entries:
        m = matches[e["no"]]
        if e["series"] != "main" and (m.row is None or m.how in ("name", "number") or m.sim < 0.5):
            twin = main_by_key.get(name_key(e["name"]))
            if twin is None:
                keys = difflib.get_close_matches(name_key(e["name"]), list(main_by_key), n=1, cutoff=0.88)
                twin = main_by_key[keys[0]] if keys else None
            if twin is not None:
                list_links[e["no"]] = twin["no"]

    variants: dict[str, set[str]] = defaultdict(set)
    district_seen: dict[str, set[str]] = defaultdict(set)
    unmatched = []
    placed: dict[int, str] = {}
    for e in sorted(entries, key=lambda e: e["series"] != "main"):  # Dénombrement entries first
        m = matches[e["no"]]
        if e["no"] in list_links and list_links[e["no"]] in placed:
            pid = placed[list_links[e["no"]]]
            m = matches[e["no"]] = Match(None, "same name as entry " + str(list_links[e["no"]]), 1.0, "medium")
        elif m.how == "rule" and m.row is None:
            pid = entry_places[e["no"]]
            if pid not in out.places:
                out.places[pid] = {"id": pid, "kind": "settlement", "name_fr": display_name(e["name"]),
                                   "place_type": _place_type("", e["descriptors"]), "source_page": e["page"],
                                   "confidence": "medium", "notes": "set in rules.yaml (entry_places)"}
                used_ids.add(pid)
        elif m.row is not None:
            pid = place_for_row(m.row, e, m)
        else:
            unmatched.append(e)
            district_seat = (e.get("district") or "").split("-", 1)[-1]
            pid = slug(display_name(e["name"])) or f"entry-{e['no']}"
            if pid in out.places and out.places[pid]["kind"] == "territory" or pid in used_ids and pid not in out.places:
                pid = f"{pid}-{district_seat}"
            if pid not in out.places:
                out.places[pid] = {"id": pid, "kind": "settlement", "name_fr": display_name(e["name"]),
                                   "place_type": _place_type("", e["descriptors"]), "source_page": e["page"],
                                   "confidence": "low", "notes": "not found in the index"}
                used_ids.add(pid)
        placed[e["no"]] = pid
        variants[pid].add(e["name"])
        p = out.places[pid]
        p.setdefault("modern_country", "")
        if p.get("confidence") == "high" and m.confidence != "high":
            p["confidence"] = m.confidence
        e["place_id"] = pid
        e["match"] = m
        if e.get("district"):
            district_seen[pid].add(key_map[e["district"]])
    # The index's links: every place an entry names, the matched one first.
    by_no = {e["no"]: e for e in entries}
    for x in resolution.links:
        if x.entry is None or x.status in ("unresolved", "no entry"):
            continue
        e = by_no[x.entry]
        pid = place_for_row(x.row, e, None)
        if pid != e["place_id"] and pid not in e.setdefault("also", []):
            e["also"].append(pid)
            variants[pid].add(e["name"])
        out.index_links.append({"place_id": pid, "entry_no": str(x.entry), "index_name": display_name(x.row.entry.name),
                                "printed": x.printed if x.printed != str(x.entry) else "", "status": x.status,
                                "source_page": x.row.page, "confidence": "high" if x.sim >= 0.5 else "medium",
                                "notes": x.note, "_row": id(x.row)})
    # rules.yaml index_spellings: the index's spellings of an entry that no surviving index line
    # carries (a line the editor's corrections deleted, a footnote): {entry: [spelling, …]}.
    for no, names in (rules.get("index_spellings") or {}).items():
        e = by_no[int(no)]
        for name in names:
            out.index_links.append({"place_id": e["place_id"], "entry_no": str(no), "index_name": name, "printed": "",
                                    "status": "manual", "source_page": e["page"], "confidence": "medium",
                                    "notes": "rules.yaml index_spellings", "_row": None})
    # The editor's table of old forms: an old spelling next to the 1870 name of an index line.
    by_index_name: dict[str, set[str]] = defaultdict(set)
    for x in out.index_links:
        by_index_name[name_key(x["index_name"])].add(x["place_id"])
    for f in old_forms:
        if f.get("ok") != "1" or not f["modern"]:
            continue
        for pid in by_index_name.get(name_key(display_name(f["modern"])), ()):
            forms = out.places[pid].setdefault("_old", [])
            old = clean.fix_name(f["old"].strip(" ."))
            if old not in forms:
                forms.append(old)
    for p in out.places.values():
        if p.get("_old"):
            p["old_forms"] = "|".join(p.pop("_old"))
    for pid, names in variants.items():
        p = out.places[pid]
        p["variants"] = "|".join(sorted(n for n in names if n != p["name_fr"]))

    # --- curated entries, memberships, holdings ---
    duke_realms = {k for k, p in out.places.items() if p.get("holder_id") == DUKE}
    seen_links = set()
    holding_rows: dict[tuple, dict] = {}
    for e in entries:
        district = key_map.get(e["district"]) if e.get("district") else None
        realm = key_map.get(e["realm"]) if e.get("realm") else None
        section = e["section"] or None
        hs = realm_holders(realm)
        if section == "other" and realm in duke_realms:
            section = "domain"  # listed under a realm of the duke with no section heading
        elif section == "other" and hs:
            section = "fief"
        holder = []
        if section == "domain" or section == "safeguard":
            holder = [DUKE]
        elif section in ("fief", "clergy") and hs and hs != [DUKE]:
            holder = hs
        m: Match = e["match"]
        notes = []
        if m.how not in ("number+name", "rule"):
            notes.append(f"index match by {m.how} ({m.sim:.2f})")
        if e["section"] == "other" and section != "other":
            notes.append(f"section {section} inferred from the realm's holder")
        notes += [f for f in e.get("flags", []) if not f.startswith("no section heading")]
        out.entries.append({
            "no": e["no"], "text": e["text"], "name": e["name"], "descriptors": "|".join(dict.fromkeys(e["descriptors"])),
            "district_id": district or "", "realm_id": realm or "", "section": section or "",
            "holder_id": "|".join(holder) if section != "domain" else "", "share": e.get("share") or "",
            "share_with": "", "series": e["series"], "order": e.get("order") or "", "place_id": e["place_id"],
            "source_page": e["page"], "confidence": m.confidence, "notes": "; ".join(notes),
        })
        for pid in [e["place_id"], *e.get("also", [])]:
            if e["series"] == "main":
                for rel, parent in (("admin", district), ("feudal", realm)):
                    if parent and (pid, parent, rel) not in seen_links:
                        seen_links.add((pid, parent, rel))
                        out.memberships.append({"child_id": pid, "parent_id": parent, "relation": rel,
                                                "share": "part" if e.get("share") == "part" and rel == "admin" else "",
                                                "source_page": e["page"]})
                if section in ("domain", "fief", "clergy", "safeguard"):
                    for h in holder or [""]:
                        share = e.get("share") or ("joint" if len(holder) > 1 else "")
                        key = (pid, section, h, share)
                        row = holding_rows.setdefault(key, {"place_id": pid, "tenure": section, "holder_id": h,
                                                            "share": share, "share_with": "", "via_entry": [],
                                                            "source_page": e["page"]})
                        row["via_entry"].append(str(e["no"]))
    for row in holding_rows.values():
        row["via_entry"] = "|".join(row["via_entry"])
        # "1/2" twice for one holder at one place is the same half, listed under two headings.
        out.holdings.append(row)
    _fix_shares(out)

    # --- membership dedupe, features ---
    uniq, seen = [], set()
    for mrow in out.memberships:
        k = (mrow["child_id"], mrow["parent_id"], mrow["relation"])
        if k not in seen:
            seen.add(k)
            uniq.append(mrow)
    out.memberships = uniq
    for f in read_jsonl(config.EXTRACTED_DIR / "features.jsonl"):
        out.features.append({k: f.get(k, "") for k in ("id", "theme", "name", "place_id", "attrs", "source_page")})

    out.report = _report(out, entries, matches, unmatched, district_seen, territories, key_map, corr_log,
                         unresolved_holders, rows)
    out.resolution = resolution
    out.report += ["", "## Index communes and cantons, spelling set", "",
                   f"- {len(commune_fixes)} spellings set to the index's usual one: "
                   + "; ".join(commune_fixes[:400])]
    out.entries_raw = entries
    return out


def _seat_key(name: str) -> str:
    """A commune or canton as the index prints it, for comparing: no footnote marks, no "de",
    the scan's Y for V at the start ("Yal-d'Ajol"), "-Nord"/"-Sud" kept."""
    n = re.sub(r"^(?:canton\s+)?(?:de\s+la\s+|de\s+|d['’]\s*|du\s+|dc\s+|d<;\s*|«le\s+|«\s*)", "", name.strip(), flags=re.I)
    n = re.sub(r"[*\d'’!°)]+$", "", n).strip(" .,;")
    n = re.sub(r"^Y(?=[aeiouéè])", "V", clean.fix_name(n))
    n = re.sub(r"(?:(?<=n)|(?<=our))l(?=$|-)", "t", n)     # "Gelvécourl", "Sainl-Dié": t read as l (not Perl)
    return n.replace("1'", "l'")


_OCR_DAMAGE = re.compile(r"[^A-Za-zÀ-ÖØ-öø-ÿ'’ .()\-]|\d|ii|ï|^(?:Y[aeiouéè]|ll|fl|il|Il|«)|[a-zà-ÿ][A-Z]"
                         r"|(?:nl|rl|cl|sl)(?:\b|-)")


def _garbled(name: str) -> bool:
    """Does the scan show in this name? "Saint-Michel" is a name; "Sainl-Mihlel", "Yittel" are not."""
    return bool(_OCR_DAMAGE.search(name.strip(" .*'’")))


def _canonical_seats(rows) -> list[str]:
    """The index's communes and cantons, OCR-garbled now and then ("Bouzonviiie"), set to the
    spelling the index prints most: a canton named on other lines, or a line of its own."""
    from collections import Counter as _C
    seen: _C = _C()
    for r in rows:
        for v in (r.entry.canton, r.entry.commune, r.entry.near):
            if v:
                seen[_seat_key(v)] += 1
        if not r.entry.xref:
            seen[_seat_key(display_name(r.entry.name))] += 2   # a line of its own: a commune
    known: dict[str, str] = {}
    for k, n in seen.most_common():           # the most printed clean spelling of each name first
        if n >= 2 and len(name_key(k)) >= 3 and not _garbled(k):
            known.setdefault(name_key(k), k)
    keys = list(known)
    log, cache = [], {}

    def fix(v: str) -> str:
        if v in cache:
            return cache[v]
        k = _seat_key(v)
        best = None
        if _garbled(v) and _garbled(k):       # misread past cleaning: a clean spelling the index prints more?
            nk = name_key(k)
            best = known.get(nk)
            if best is None and len(nk) >= 5:
                close = [c for c in difflib.get_close_matches(nk, keys, n=3, cutoff=0.8)
                         if c[0] == nk[0] and abs(len(c) - len(nk)) <= 1]
                best = known[close[0]] if close else None
            if best is not None and seen[best] <= seen[k]:
                best = None
        cache[v] = best or k
        if cache[v] != v:
            log.append(f"{v} → {cache[v]}")
        return cache[v]

    for r in rows:
        e = r.entry
        e.canton = fix(e.canton) if e.canton else e.canton
        e.commune = fix(e.commune) if e.commune else e.commune
        e.near = fix(e.near) if e.near else e.near
    return sorted(set(log))


def split_entries(entries: list[dict], rules: dict) -> list[dict]:
    """rules.yaml `entry_splits`: entries the scan ran together, as printed
    ({read no: [{no, text}, …]}): "1514. outzweillcr.Kxweiller." is 1513 Exweiller and 1514 Sutzweiller."""
    splits = {int(k): v for k, v in (rules.get("entry_splits") or {}).items()}
    out = []
    for e in entries:
        if e["no"] not in splits:
            out.append(e)
            continue
        for part in splits.pop(e["no"]):
            text = part["text"]
            out.append({**e, "no": int(part["no"]), "text": text, "name": text.rstrip(" ."),
                        "descriptors": [], "flags": [*e.get("flags", []), "split by rules.yaml (entry_splits)"]})
    if splits:
        raise ValueError(f"rules.yaml entry_splits: no entry {sorted(splits)}")
    return out


def _fix_shares(out: Built) -> None:
    """Fractions held by different holders at one place may not exceed the whole: when the
    book gives "pour la moitié" under two headings, both halves are the same holder's."""
    by_place = defaultdict(list)
    for h in out.holdings:
        by_place[h["place_id"]].append(h)
    for rows in by_place.values():
        halves = [h for h in rows if h["share"] == "1/2"]
        if len(halves) > 2:
            for h in halves[2:]:
                h["share"] = "part"


def _report(out, entries, matches, unmatched, district_seen, territories, key_map, corr_log, unresolved, rows) -> list[str]:
    main = [e for e in entries if e["series"] == "main"]
    with_place = [e for e in main if matches[e["no"]].row is not None or matches[e["no"]].how == "rule"]
    unmatched = [e for e in unmatched if not matches[e["no"]].how.startswith("same name")]
    hows = Counter("same name as a Dénombrement entry" if matches[e["no"]].how.startswith("same name")
                   else matches[e["no"]].how for e in entries)
    lines = ["# Stage 4: review report", "",
             "Generated by `make curate`. Decisions go into `data/curated/rules.yaml` or `data/curated/manual/`.", "",
             "## Identification", "",
             f"- Dénombrement entries matched to an index line: {len(with_place)}/{len(main)} "
             f"({100 * len(with_place) / max(1, len(main)):.1f}%).",
             f"- How all {len(entries)} entries were matched: {dict(hows)}.",
             f"- Places: {sum(p['kind'] == 'settlement' for p in out.places.values())} settlements, "
             f"{sum(p['kind'] == 'territory' for p in out.places.values())} territories.",
             f"- Index lines no entry claims: {sum(1 for r in rows if not r.deleted and not r.entry.xref and id(r) not in {id(m.row) for m in matches.values() if m.row})}.",
             "", "### Entries not found in the index", ""]
    lines += [f"- {e['no']} {e['name']} (p. {e['page']}, {e['district']})" for e in unmatched] or ["- none"]
    lines += ["", "### Matched by a confused number or by name alone (check)", "",
              "| no | entry | index line | how | similarity |", "|---|---|---|---|---|"]
    for e in entries:
        m = matches[e["no"]]
        if m.how in ("confused number", "name") or (m.how == "number" and m.sim < 0.35):
            lines.append(f"| {e['no']} | {e['name']} | {m.row.entry.name if m.row else ''} | {m.how} | {m.sim:.2f} |")
    lines += ["", "### Places in more than one bailliage (homonyms or misread numbers?)", ""]
    parents = {mm["child_id"]: mm["parent_id"] for mm in out.memberships if mm["relation"] == "admin"
               and out.places.get(mm["child_id"], {}).get("kind") == "territory"}

    def bailliage(t: str) -> str:
        seen = set()
        while t in parents and t not in seen:
            seen.add(t)
            if out.places[t]["place_type"] == "bailiwick" or parents[t] == DUKE:
                return t
            t = parents[t]
        return t
    multi = 0
    for pid, ds in district_seen.items():
        bs = {bailliage(d) for d in ds}
        if len(bs) > 1:
            multi += 1
            lines.append(f"- `{pid}` ({out.places[pid]['name_fr']}): {', '.join(sorted(bs))}")
    if not multi:
        lines.append("- none")
    lines += ["", "## Territories", ""]
    no_holder = [k for k, p in out.places.items() if p.get("hierarchy") == "feudal" and not p.get("holder_id")]
    lines += [f"- Realms without a holder ({len(no_holder)}): " + ", ".join(f"`{k}`" for k in no_holder)]
    no_ressort = [k for k, p in out.places.items() if p.get("hierarchy") == "feudal"
                  and not any(mm["child_id"] == k and mm["relation"] in ("ressort", "feudal") for mm in out.memberships)]
    lines += [f"- Realms without a ressort or a parent realm ({len(no_ressort)}): " + ", ".join(f"`{k}`" for k in no_ressort)]
    lines += ["- Holder phrases not resolved (add to `realm_holders`):", *(unresolved or ["  - none"])]
    lines += ["", "## Sections inferred", ""]
    other = Counter((e["district_id"], e["realm_id"]) for e in out.entries if e["series"] == "main" and e["section"] == "other")
    lines += [f"- {n} entries still `other` in `{d}`" + (f" / `{r}`" if r else "") for (d, r), n in other.most_common()] or ["- none"]
    lines += ["", "## Shares", ""]
    for e in out.entries:
        if e["share"]:
            src = next(x for x in entries if x["no"] == e["no"])
            lines.append(f"- {e['no']} {e['name']}: {e['share']} — \"{src.get('share_text', '')[:80]}\"")
    lines += ["", "## Corrections applied to the index", "", *corr_log, ""]
    return lines


def write(out: Built) -> None:
    def dump(model, rows):
        cols = model.columns()
        path = config.CURATED_DIR / f"{model.table}.csv"
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") if r.get(c) is not None else "" for c in cols})
    dump(models.Entry, out.entries)
    dump(models.Place, sorted(out.places.values(), key=lambda p: (p["kind"] != "territory", p["id"])))
    dump(models.Membership, out.memberships)
    dump(models.Entity, sorted(out.entities.values(), key=lambda e: e["id"]))
    dump(models.Holding, out.holdings)
    dump(models.Feature, out.features)
    links, seen = [], set()
    for x in sorted(out.index_links, key=lambda x: (x["place_id"], int(x["entry_no"]))):
        key = (x["place_id"], x["entry_no"], name_key(x["index_name"]))
        if key not in seen:   # two index lines of one spelling merged into one place
            seen.add(key)
            links.append(x)
    dump(models.IndexLink, links)
    # Japanese names (the app's fourth language), keyed by the final ids; manual ones win.
    ja = {p["id"]: p["_name_ja"] for p in out.places.values() if p.get("_name_ja")}
    for r in load_manual("names_ja"):
        ja[r["id"]] = (r["name_ja"], "manual")
    with (config.CURATED_DIR / "names_ja.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "name_ja", "source"])
        for pid in sorted(ja):
            w.writerow([pid, *ja[pid]])
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    (REVIEW_DIR / "report.md").write_text("\n".join(out.report) + "\n")
    if out.resolution:
        counts = reconcile.write(out.resolution, out.entries, {x["_row"]: x["place_id"] for x in out.index_links})
        lines = reconcile.report(counts)
        with (REVIEW_DIR / "report.md").open("a") as f:
            f.write("\n".join(lines) + "\n")


def merge_geocoding(out: Built) -> int:
    """Stage 5's coordinates and modern names into the places (data/curated/geocoding.csv).
    Kept out of `build()`, which the geocoder reads: its names must not feed back."""
    path = config.CURATED_DIR / "geocoding.csv"
    if not path.exists():
        return 0
    n = 0
    for g in csv.DictReader(path.open()):
        p = out.places.get(g["place_id"])
        if p is None:
            continue
        n += 1
        p["geo_method"], p["geo_confidence"] = g["method"], g["confidence"]
        if g.get("name_ja"):
            p["_name_ja"] = (g["name_ja"], "wikidata" if g["method"] != "territory" else "seat + type")
        if g["lat"]:
            p["lat"], p["lon"] = g["lat"], g["lon"]
        p["wikidata_id"], p["geonames_id"] = g["wikidata_id"], g["geonames_id"]
        if p["kind"] == "settlement":
            if g["name_fr"] and g["name_fr"] != p["name_fr"]:
                # The modern name; the index's spelling joins the book's as a variant.
                variants = [v for v in (p.get("variants") or "").split("|") if v]
                p["variants"] = "|".join(dict.fromkeys(variants + [p["name_fr"]]))
                p["name_fr"] = g["name_fr"]
            p["name_de"] = g["name_de"] or p.get("name_de", "")
            p["name_en"] = g["name_en"] or p.get("name_en", "")
            if g["country"]:
                p["modern_country"] = g["country"]
            if g["note"]:
                p["notes"] = "; ".join(x for x in (p.get("notes"), g["note"]) if x)
    _merge_same_item(out)
    _report_geocoding(out)
    _rekey(out)
    _manual_memberships(out)
    _shared_lands(out)
    return n


def _manual_memberships(out: Built) -> None:
    """manual/memberships.csv: memberships the lists don't give by themselves (a territory's own
    seat, listed elsewhere), each with its page and why. Keyed by the final place ids."""
    have = {(m["child_id"], m["parent_id"], m["relation"]) for m in out.memberships}
    added = []
    for r in load_manual("memberships"):
        if r["child_id"] not in out.places or r["parent_id"] not in out.places:
            raise ValueError(f"manual/memberships.csv: unknown place in {r['child_id']} -> {r['parent_id']}")
        if (r["child_id"], r["parent_id"], r["relation"]) not in have:
            out.memberships.append({k: r.get(k, "") for k in models.Membership.model_fields if k in r})
            added.append(f"`{r['child_id']}` → `{r['parent_id']}` ({r['notes']})")
    out.report += ["", "## Memberships added by hand (manual/memberships.csv)", "",
                   *(f"- {a}" for a in added)] if added else []


def _shared_lands(out: Built) -> None:
    """A division and a realm on the same land (counterpart pairs: the office and the lordship of
    Forbach) share their lands, as in hist_map: the realm's places are in the division, and the
    division's places, its sub-divisions' included, are the realm's unless they are in another realm."""
    kids: dict[str, list[dict]] = defaultdict(list)
    for m in out.memberships:
        if m["relation"] != "ressort":
            kids[m["parent_id"]].append(m)

    def settlements(tid: str) -> dict[str, dict]:
        found, seen, queue = {}, {tid}, [tid]
        while queue:
            for m in kids.get(queue.pop(), ()):
                c = m["child_id"]
                if out.places[c]["kind"] == "settlement":
                    found.setdefault(c, m)
                elif c not in seen:
                    seen.add(c)
                    queue.append(c)
        return found

    feudal_of: dict[str, set[str]] = defaultdict(set)
    for m in out.memberships:
        if m["relation"] == "feudal":
            feudal_of[m["child_id"]].add(m["parent_id"])
    added: list[str] = []
    for a, p in sorted(out.places.items()):
        f = p.get("counterpart_id")
        if p.get("hierarchy") != "admin" or not f or f not in out.places:
            continue
        basis = p.get("counterpart_basis") or ""
        note = f"shared lands of {p['name_fr']} and {out.places[f]['name_fr']} (the same land: {basis})"
        in_a, in_f = settlements(a), settlements(f)
        for c, like in sorted(in_f.items()):
            if c not in in_a:
                out.memberships.append({"child_id": c, "parent_id": a, "relation": "admin", "share": "",
                                        "source_page": like.get("source_page", ""), "confidence": "medium",
                                        "notes": note})
                added.append(f"`{c}` → `{a}`")
        for c, like in sorted(in_a.items()):
            if c not in in_f and not (feudal_of[c] - {f}):
                out.memberships.append({"child_id": c, "parent_id": f, "relation": "feudal", "share": "",
                                        "source_page": like.get("source_page", ""), "confidence": "medium",
                                        "notes": note})
                added.append(f"`{c}` → `{f}`")
    out.report += ["", "## Shared lands of a division and its realm", "",
                   f"- {len(added)} membership(s) added: " + ", ".join(added) if added else "- none added"]


def _merge_same_item(out: Built) -> None:
    """Two index lines for one village (the geocoder left them on one Wikidata item, with the
    same canton): one place, whose variants, entries, memberships and holdings are the union."""
    groups: dict[str, list[str]] = defaultdict(list)
    for pid, p in sorted(out.places.items()):
        if p["kind"] == "settlement" and p.get("wikidata_id") and p.get("geo_confidence") in ("high", "medium"):
            groups[p["wikidata_id"]].append(pid)
    into: dict[str, str] = {}
    for pids in groups.values():
        keep = pids[0]
        for other in pids[1:]:
            into[other] = keep
            k, o = out.places[keep], out.places.pop(other)
            names = [v for v in (k.get("variants") or "").split("|") + (o.get("variants") or "").split("|")
                     + [o["name_fr"]] if v and v != k["name_fr"]]
            k["variants"] = "|".join(dict.fromkeys(names))
            forms = [v for v in (k.get("old_forms") or "").split("|") + (o.get("old_forms") or "").split("|") if v]
            k["old_forms"] = "|".join(dict.fromkeys(forms))
            k["notes"] = "; ".join(x for x in (k.get("notes"), f"merged with {other} (same Wikidata item and canton)") if x)
    if not into:
        return
    for e in out.entries:
        e["place_id"] = into.get(e["place_id"], e["place_id"])
    for x in out.index_links:
        x["place_id"] = into.get(x["place_id"], x["place_id"])
    seen, kept = set(), []
    for m in out.memberships:
        m["child_id"] = into.get(m["child_id"], m["child_id"])
        key = (m["child_id"], m["parent_id"], m["relation"])
        if key not in seen:
            seen.add(key)
            kept.append(m)
    out.memberships = kept
    merged: dict[tuple, dict] = {}
    for h in out.holdings:
        h["place_id"] = into.get(h["place_id"], h["place_id"])
        key = (h["place_id"], h["tenure"], h["holder_id"], h["share"])
        if key in merged:
            merged[key]["via_entry"] = "|".join(sorted(set(merged[key]["via_entry"].split("|") + h["via_entry"].split("|")),
                                                       key=lambda x: int(x) if x.isdigit() else 0))
        else:
            merged[key] = h
    out.holdings = list(merged.values())
    out.report.append(f"\n- Merged {len(into)} place(s) that are another index line for the same village: "
                      + ", ".join(f"`{a}` → `{b}`" for a, b in sorted(into.items())))


def _report_geocoding(out: Built) -> None:
    settlements = [p for p in out.places.values() if p["kind"] == "settlement"]
    identified = [p for p in settlements if p.get("lost") != "true"
                  and (p.get("index_canton") or p.get("index_commune") or p.get("index_dept"))]
    located = [p for p in identified if p.get("lat")]
    methods = Counter((p.get("geo_method") or "", p.get("geo_confidence") or "") for p in settlements)
    lines = ["", "## Geocoding to check (Stage 5)", "",
             f"- Settlements located: {sum(1 for p in settlements if p.get('lat'))}/{len(settlements)}; "
             f"of those the index identifies: {len(located)}/{len(identified)} "
             f"({100 * len(located) / max(1, len(identified)):.1f}%).",
             f"- By method and confidence: {dict(sorted(methods.items()))}.",
             "- Rules for these go in the `geocode` section of `rules.yaml`: "
             "`{wikidata: Q…}`, `{lat, lon}`, `{approximate: other-place}` or `{unlocated: true}`, with a `note`.",
             "", "### Identified by the index but not located", ""]
    lines += [f"- `{p['id']}` {p['name_fr']} — canton {p.get('index_canton') or '–'}, commune "
              f"{p.get('index_commune') or '–'} ({p.get('variants', '')[:40]})"
              for p in identified if not p.get("lat")] or ["- none"]
    lines += ["", "### Located with low confidence or far from their district", ""]
    lines += [f"- `{p['id']}` {p['name_fr']} ({p.get('geo_method')}): {p.get('notes', '')[-90:]}"
              for p in settlements if p.get("lat") and p.get("geo_confidence") == "low"
              and p.get("geo_method") != "approximate"] or ["- none"]
    out.report += lines


def _rekey(out: Built) -> None:
    """Settlement ids from their modern names where the location is reliable ("tholcy" -> "tholey"),
    so that ids (and the app's URLs) don't carry the index's OCR spelling."""
    taken = set(out.places)
    renames: dict[str, str] = {}
    for pid, p in sorted(out.places.items()):
        if p["kind"] != "settlement" or p.get("geo_confidence") not in ("high", "medium"):
            continue
        new = slug(p["name_fr"])
        if not new or new == pid:
            continue
        if new in taken:
            continue  # a namesake keeps its index-based id
        taken.discard(pid)
        taken.add(new)
        renames[pid] = new
    if not renames:
        return
    out.places = {renames.get(k, k): {**v, "id": renames.get(k, k)} for k, v in out.places.items()}
    for e in out.entries:
        e["place_id"] = renames.get(e["place_id"], e["place_id"])
    for m in out.memberships:
        m["child_id"] = renames.get(m["child_id"], m["child_id"])
        m["parent_id"] = renames.get(m["parent_id"], m["parent_id"])
    for h in out.holdings:
        h["place_id"] = renames.get(h["place_id"], h["place_id"])
    for x in out.index_links:
        x["place_id"] = renames.get(x["place_id"], x["place_id"])
    for f in out.features:
        f["place_id"] = renames.get(f["place_id"], f["place_id"]) if f.get("place_id") else f.get("place_id")
    # The review report names places by their ids too.
    out.report = [_rename_in(line, renames) for line in out.report]


def _rename_in(line: str, renames: dict[str, str]) -> str:
    return re.sub(r"`([a-z0-9-]+)`", lambda m: f"`{renames.get(m.group(1), m.group(1))}`", line)
