"""DicoTopo (Dictionnaire topographique de la France, CTHS / École des chartes): every commune,
hamlet, farm and mill of Meurthe (Lepage 1862), Meuse (Liénard 1872), Moselle (Bouteiller 1874)
and Vosges (Marichal 1941), with their dated old spellings. A prototype: it suggests the place an
OCR-garbled name of the Dénombrement stands for, matching it against those old spellings with an
edit distance that makes this scan's letter confusions cheap; nothing is written to the dataset."""
from __future__ import annotations

import csv
import difflib
import html
import json
import multiprocessing
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date

import requests

from denombrement import config
from denombrement.curate.build import fold, load_rules
from denombrement.geo.geocode import km
from denombrement.geo.wikidata import HEADERS

API = "https://dicotopo.cths.fr/api/1.0/search"
CACHE_DIR = config.RAW_DIR / "geo_cache" / "dicotopo"
DEPARTEMENTS = ("54", "55", "57", "88")
REVIEW_FILE = config.DATA_DIR / "review" / "dicotopo.md"
MANUAL_CHECK = config.DATA_DIR / "review" / "manual-check.md"


def _fetch(dpt: str) -> list[dict]:
    """A département's places; the search stops at 10,000 hits, so it is asked in ten slices by place id."""
    out = []
    for digit in "0123456789":
        url = f"{API}?query=dep-id:{dpt} AND type:place AND place-id:P{digit}*&page[size]=1000&sort=place-id"
        while url:
            r = requests.get(url, headers=HEADERS, timeout=120)
            r.raise_for_status()
            d = r.json()
            for item in d["data"]:
                a = item["attributes"]
                lonlat = re.findall(r"-?\d+\.\d+", a.get("longlat") or "")
                out.append({"id": a["place-id"], "label": a["place-label"], "old": a.get("old-labels") or [],
                            "insee": a.get("localization-insee-code"), "commune": a.get("commune-label"),
                            "dpt": dpt, "canton": a.get("canton"),
                            "lat": float(lonlat[1]) if lonlat else None, "lon": float(lonlat[0]) if lonlat else None,
                            "description": " ".join(a.get("descriptions") or [])})
            url = d["links"].get("next")
    return out


def _downloaded() -> str:
    """When the cache was filled: the date the Licence Ouverte's attribution asks for."""
    times = [p.stat().st_mtime for p in CACHE_DIR.glob("*.json")]
    return date.fromtimestamp(max(times)).isoformat() if times else "?"


def region() -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for dpt in DEPARTEMENTS:
        path = CACHE_DIR / f"{dpt}.json"
        if not path.exists():
            path.write_text(json.dumps(_fetch(dpt), ensure_ascii=False), encoding="utf-8")
        out.extend(json.loads(path.read_text(encoding="utf-8")))
    return out


_DFN = re.compile(r"<dfn>(.*?)</dfn>")
_DATE = re.compile(r"\((\d{3,4})")


def old_labels(place: dict) -> list[tuple[str, str]]:
    """(spelling, year) pairs: "<dfn>Aubocurt</dfn> et <dfn>Aubocourt</dfn> (1178)" is two; of a
    quoted phrase ("Hennezel et Reuxeulles, hameau, communauté de Tendon") only the name before the comma."""
    out = []
    for raw in place["old"]:
        date = _DATE.search(raw)
        for n in _DFN.findall(raw):
            n = html.unescape(re.sub(r"<[^>]+>", "", n)).split(",")[0].strip()
            out.extend((part, date.group(1) if date else "") for part in re.split(r"\s+(?:et|ou)\s+", n))
    return out


def kind(place: dict) -> str:
    """The dictionary's word for the place: "Écart", "Ferme", "Hameau", "Lieu dit"; "" for a commune."""
    k = re.split(r"[,.;]", re.sub(r"<[^>]+>", "", place["description"]))[0].strip()
    return "" if k.startswith(("Canton de", "Chef-lieu", "Village", "À ")) else k


# a field, wood or stream is seldom what the Dénombrement names
_LAND = ("Lieu dit", "Contrée", "Bois", "Ruisseau", "Fontaine", "Étang", "Montagne", "Côte", "Canton forestier",
         "Affluent", "Rivière", "Source", "Forêt", "Ravin", "Chemin", "Pré", "Roche", "Col", "Vallée", "Mont", "Gorge")


# --- an edit distance for this scan's OCR and for 16th-century spelling -----------------------

def spelling_key(name: str) -> str:
    """Old and modern spellings brought together: no accents, articles or spaces; Sainct = Saint;
    y = i, doubled letters single, a final s/x/z dropped (Flainvaulx = Flainval)."""
    f = fold(name)
    f = re.sub(r"^(?:la|le|les|l')\s+|\((?:la|le|les|l')\)", "", f)
    f = f.replace("sainct", "saint").replace("ste-", "sainte-").replace("st-", "saint-")
    f = re.sub(r"[^a-z]", "", f).replace("y", "i").replace("cq", "c").replace("ck", "c")
    f = re.sub(r"(.)\1+", r"\1", f)
    f = re.sub(r"(?<=[aeiou])(?:lx|ulx|ux)$", "l", f)  # Flainvaulx, Fleinvalz -> -al/-aul
    return re.sub(r"[sxz]$", "", f)


_CHEAP = 0.35
# single-letter confusions of this scan (c/e, l/t, b/h as in Stage 4's keys) and of old spelling
_PAIRS = {frozenset(p) for p in ("ce", "lt", "bh", "nu", "il", "ij", "uv", "oe", "fs", "rt", "ae", "co", "on", "ao",
                                 "ft", "ie", "gq", "mn", "ei", "au")}
# multi-letter confusions: "Hainvau" is Flainvau, "Gloi»ville" Glonville; li/h, rn/m, ii/u, cl/d
_MULTI = [("fl", "h"), ("li", "h"), ("rn", "m"), ("ii", "u"), ("cl", "d"), ("in", "m"), ("ri", "n"), ("ni", "m"),
          ("ui", "m"), ("oi", "on"), ("ai", "e"), ("ei", "e"), ("au", "o"), ("ou", "o"), ("ff", "f")]
_MULTI += [(b, a) for a, b in _MULTI]


_SUB = {(a, b): _CHEAP for pair in _PAIRS for a in pair for b in pair if a != b}
# the multi-letter rules by their last letters, the only ones that can end at a cell
_MULTI_AT: dict[tuple[str, str], list[tuple[str, str, int, int]]] = defaultdict(list)
for _x, _y in _MULTI:
    _MULTI_AT[(_x[-1], _y[-1])].append((_x, _y, len(_x), len(_y)))


def _sub(a: str, b: str) -> float:
    return 0.0 if a == b else _SUB.get((a, b), 1.0)


def ocr_distance(a: str, b: str) -> float:
    """Weighted Levenshtein between two spelling keys."""
    n, m = len(a), len(b)
    d = [[float(j) for j in range(m + 1)]] + [[float(i)] + [0.0] * m for i in range(1, n + 1)]
    for i in range(1, n + 1):
        ai, row, prev = a[i - 1], d[i], d[i - 1]
        for j in range(1, m + 1):
            bj = b[j - 1]
            best = min(prev[j] + 1, row[j - 1] + 1, prev[j - 1] + (0.0 if ai == bj else _SUB.get((ai, bj), 1.0)))
            for x, y, lx, ly in _MULTI_AT.get((ai, bj), ()):
                if i >= lx and j >= ly and a[i - lx:i] == x and b[j - ly:j] == y:
                    best = min(best, d[i - lx][j - ly] + _CHEAP)
            row[j] = best
    return d[n][m]


_COARSE = str.maketrans("eoauictbhfsnmrjyvq", "eeeeiilhhssnnnilug")


def coarse(key: str) -> str:
    """A key with the confusable letters merged, for a quick first sift."""
    for x, y in (("fl", "h"), ("li", "h"), ("rn", "m"), ("ii", "u"), ("cl", "d")):
        key = key.replace(x, y)
    return key.translate(_COARSE)


def _pairs(key: str) -> set[str]:
    return {key[i:i + 2] for i in range(len(key) - 1)}


def similarity(a: str, b: str) -> float:
    if not a or not b or abs(len(a) - len(b)) > max(3, len(a) // 2):
        return 0.0
    return max(0.0, 1 - ocr_distance(a, b) / max(len(a), len(b)))


# --- matching ------------------------------------------------------------------------------------

_LEAD = re.compile(r"^(?:la\s+)?(?:ville|bourg|chasteau|chastel|cense|moulin|maison)\s+(?:de\s+|du\s+|dudict\s+|d')?|"
                   r"^(?:le|la|les|l')\s+", re.I)


def query_keys(name: str) -> list[tuple[str, float]]:
    """The entry's name without "La ville dudict" and the like, then each long word of it, which counts less."""
    clean = _LEAD.sub("", re.sub(r"\b(?:dudict|dudit|ledict|ladicte)\b\s*", "", name, flags=re.I)).strip()
    out = [(spelling_key(clean), 1.0)]
    words = [w for w in re.split(r"[\s-]+", clean) if len(spelling_key(w)) >= 4]
    if len(words) > 1:
        out.extend((spelling_key(w), 0.85) for w in words)
    return [(k, w) for k, w in out if k]


@dataclass
class Hit:
    place: dict
    spelling: str
    year: str
    score: float
    km: float | None


class Index:
    def __init__(self, places: list[dict]):
        self.labels: dict[str, list[tuple[dict, str, str]]] = defaultdict(list)
        self.coarse: dict[str, str] = {}
        self.postings: dict[str, list[int]] = defaultdict(list)  # letter pair of a coarse key -> keys
        for p in places:
            p["kind"] = kind(p)
            for name, year in [(p["label"], ""), *old_labels(p)]:
                for part in re.split(r"\s+ou\s+", name):  # "Aboncourt ou Aboncourt-sur-Seille"
                    k = spelling_key(re.sub(r"\s*\(.*?\)", "", part))  # "Corps-Mort (Chemin du)"
                    if len(k) >= 3:
                        self.labels[k].append((p, part, year))
                        self.coarse[k] = coarse(k)
        self.keys = list(self.labels)
        for i, k in enumerate(self.keys):
            for pair in _pairs(self.coarse[k]):
                self.postings[pair].append(i)

    def candidates(self, qk: str) -> list[str]:
        """Keys sharing at least 40% of the query's letter pairs: a cheap first cut before the sift."""
        pairs = _pairs(coarse(qk))
        counts: dict[int, int] = defaultdict(int)
        for pair in pairs:
            for i in self.postings.get(pair, ()):
                counts[i] += 1
        need = max(1, int(0.4 * len(pairs)))
        return [self.keys[i] for i in sorted(i for i, n in counts.items() if n >= need)]

    def search(self, name: str, near: tuple[float, float] | None = None, limit: int = 5) -> list[Hit]:
        best: dict[str, Hit] = {}
        for qk, weight in query_keys(name):
            sift = difflib.SequenceMatcher(None, "", coarse(qk))
            for k in self.candidates(qk):
                refs = self.labels[k]
                sift.set_seq1(self.coarse[k])
                if sift.real_quick_ratio() < 0.7 or sift.quick_ratio() < 0.7:
                    continue
                s = weight * similarity(qk, k)
                if s < 0.6:
                    continue
                for p, spelling, year in refs:
                    dist = km(near, (p["lat"], p["lon"])) if near and p["lat"] is not None else None
                    # a namesake far from the entry's district counts less: 0.1 off per 50 km
                    score = s - (min(dist, 150) / 500 if dist is not None else 0.05)
                    score -= 0.08 if p["kind"].startswith(_LAND) or "(" in p["label"] else 0
                    if p["id"] not in best or score > best[p["id"]].score:
                        best[p["id"]] = Hit(p, spelling, year, score, dist)
        return sorted(best.values(), key=lambda h: -h.score)[:limit]


# --- the prototype run: manual-check entries and the places still unlocated ----------------------

def _csv(name: str) -> list[dict]:
    with open(config.CURATED_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def district_centres() -> dict[str, tuple[float, float]]:
    """Median of each district's located members. From places.csv: geocoding.csv keeps the ids
    the places had before curate renamed some."""
    located = {p["id"]: (float(p["lat"]), float(p["lon"])) for p in _csv("places.csv")
               if p["kind"] == "settlement" and p["lat"] and p["geo_confidence"] != "low"}
    members = defaultdict(list)
    for m in _csv("memberships.csv"):
        if m["relation"] == "admin" and m["child_id"] in located:
            members[m["parent_id"]].append(located[m["child_id"]])
    out = {}
    for t, pts in members.items():
        if len(pts) >= 3:
            lats, lons = sorted(a for a, _ in pts), sorted(b for _, b in pts)
            out[t] = (lats[len(lats) // 2], lons[len(lons) // 2])
    return out


_CHECK = re.compile(r"^- (\d+) (.+?) \(p\. \d+, ([^)]+)\)\s*$")


def manual_checks() -> list[tuple[str, str, str, str]]:
    """(entry no, name, district, the answer found by hand) from data/review/manual-check.md."""
    out = []
    if not MANUAL_CHECK.exists():
        return out
    for line in MANUAL_CHECK.read_text(encoding="utf-8").splitlines():
        if m := _CHECK.match(line):
            out.append([m.group(1), m.group(2), m.group(3), ""])
        elif line.strip().startswith("+ ") and out:
            out[-1][3] = line.strip()[2:]
    return [tuple(o) for o in out]


def _answer_rank(hits: list[Hit], answer: str) -> int | None:
    """Where the hand-found answer's first name ("Flainval (written Flainvau)") is among the hits."""
    want = spelling_key(re.split(r"\s*\(", answer)[0])
    for i, h in enumerate(hits, 1):
        if want and want in {spelling_key(h.place["label"].split(" ou ")[0]), spelling_key(h.place["commune"] or "")}:
            return i
    return None


def _row(h: Hit) -> str:
    where = ", ".join(x for x in (h.place["kind"], h.place["commune"] if h.place["commune"] != h.place["label"] else "",
                                  f"canton {h.place['canton']}" if h.place["canton"] else "", h.place["dpt"]) if x)
    seen = f"{h.spelling} ({h.year})" if h.year else h.spelling
    dist = f"{h.km:.0f} km" if h.km is not None else "?"
    return f"{h.place['label']} [{where}] via *{seen}*, {h.score:.2f}, {dist}"


_INDEX: Index | None = None  # the worker processes' index, inherited by fork


def _search(query: tuple[str, tuple[float, float] | None, int]) -> list[Hit]:
    return _INDEX.search(*query)


def search_all(idx: Index, queries: list[tuple[str, tuple[float, float] | None, int]]) -> list[list[Hit]]:
    """Each query's hits, the queries shared out among the CPUs: the matching is pure Python."""
    global _INDEX
    _INDEX = idx
    with multiprocessing.get_context("fork").Pool(os.cpu_count()) as pool:
        return pool.map(_search, queries, chunksize=1)


def display_label(label: str) -> str:
    """DicoTopo's headword as a name: "Orme (L’)" -> "L’Orme", "Aboncourt ou Aboncourt-sur-Seille" -> Aboncourt."""
    label = label.split(" ou ")[0].strip()
    m = re.match(r"^(.*?)\s*\((L[’']|Le|La|Les)\)$", label)
    if m:
        art = m.group(2)
        return f"{art}{m.group(1)}" if art in ("L’", "L'") else f"{art} {m.group(1)}"
    return label


def shared_points(places: list[dict]) -> set[tuple[float, float]]:
    """Points that several places share: a commune's, given to the hamlets the dictionary has no point
    for (whatever the commune is called there: Kerling-lez-Sierck). A hamlet's own point is not among them."""
    seen = Counter((p["lat"], p["lon"]) for p in places if p["lat"] is not None)
    return {pt for pt, n in seen.items() if n > 1}


REVIEW_MIN = 0.8      # a match this good names an approximate place
DISAGREE_MIN = 0.85   # a match this good, far from the place, is worth a look
NEAR_KM = 12.0        # the match is the place where it is now
FAR_KM = 15.0


def review_settlements(idx: Index, places: dict, parents: dict, centres: dict, shared: set,
                       reviewed: dict | None = None) -> list[str]:
    """Every located settlement's names (the index's and the book's) against DicoTopo, scored near its
    district, not near where it is placed: names for places put at their commune under the index's
    garbled spelling, and matches that disagree with the placement."""
    settlements = [p for p in places.values() if p["kind"] == "settlement" and p["lat"]]
    queries, owners = [], []
    for p in settlements:
        near = [centres[t] for t in parents.get(p["id"], []) if t in centres]
        near = (sum(a for a, _ in near) / len(near), sum(b for _, b in near) / len(near)) if near else None
        names = {spelling_key(n): n for n in [p["name_fr"], *(p["variants"] or "").split("|")] if n.strip()}
        for n in names.values():
            queries.append((n, near, 3))
            owners.append((p["id"], near, n))
    best: dict[str, tuple[Hit, str, tuple | None]] = {}
    for (pid, near, name), hits in zip(owners, search_all(idx, queries)):
        if hits and (pid not in best or hits[0].score > best[pid][0].score):
            best[pid] = (hits[0], name, near)

    reviewed = reviewed or {}
    named, disagree, silenced = [], [], 0
    for p in settlements:
        if p["id"] not in best:
            continue
        h, name, near = best[p["id"]]
        if h.place["lat"] is None:
            continue
        here = (float(p["lat"]), float(p["lon"]))
        hit = (h.place["lat"], h.place["lon"])
        moved = km(here, hit)
        own = hit not in shared
        label = display_label(h.place["label"])
        where = ", ".join(x for x in (h.place["kind"], h.place["commune"] if h.place["commune"] != label else "",
                                      h.place["dpt"]) if x)
        seen = f"*{h.spelling}* ({h.year})" if h.year else f"*{h.spelling}*"
        if not (p["wikidata_id"] or p["geonames_id"]) and h.score >= REVIEW_MIN and moved <= NEAR_KM:
            if spelling_key(label) != spelling_key(p["name_fr"]) or (own and moved > 0.5):
                point = f"; its own point {hit[0]:.5f}, {hit[1]:.5f} ({moved:.1f} km)" if own and moved > 0.5 else ""
                named.append((h.score, f"- `{p['id']}` {p['name_fr']} → **{label}** [{where}] via {name!r} ~ {seen}, "
                                       f"{h.score:.2f}{point}"))
        elif h.score >= DISAGREE_MIN and moved > FAR_KM and near and h.km is not None \
                and h.km + 10 < km(here, near):
            if p["id"] in reviewed:   # checked by hand: the placement stands
                silenced += 1
                continue
            disagree.append((moved, f"- `{p['id']}` {p['name_fr']} ({p['geo_method']}/{p['geo_confidence']}), "
                                    f"{km(here, near):.0f} km from its district → **{label}** [{where}] via {name!r} ~ {seen}, "
                                    f"{h.score:.2f}, {h.km:.0f} km from its district, {moved:.0f} km from where it is"))
    return ([f"## Settlements at their commune: DicoTopo's name ({len(named)})", "",
             "Approximate places (no Wikidata or GeoNames item) with a match within 12 km: the modern name, and",
             "the hamlet's own point where DicoTopo gives one (not its commune's).", ""]
            + [line for _, line in sorted(named, key=lambda x: -x[0])]
            + ["", f"## Settlements DicoTopo places elsewhere ({len(disagree)})", "",
               f"A match of {DISAGREE_MIN} or better more than {FAR_KM:.0f} km from where the place is, and nearer its district"
               + (f"; {silenced} more checked by hand (rules.yaml `dicotopo_reviewed`)." if silenced else "."), ""]
            + [line for _, line in sorted(disagree, key=lambda x: -x[0])])


def run() -> None:
    dico = region()
    idx = Index(dico)
    centres = district_centres()
    entries = {e["no"]: e for e in _csv("entries.csv") if e["series"] == "main"}
    lines = ["# DicoTopo suggestions", "",
             "Prototype: OCR-aware matching of names against the old spellings of the Dictionnaire topographique",
             "(Meurthe, Meuse, Moselle, Vosges). Score: spelling similarity less 0.1 per 50 km from the district.", "",
             "Source: DicoTopo, Dictionnaire topographique de la France, CTHS, École nationale des chartes and",
             f"Archives nationales, <https://dicotopo.cths.fr>, Licence Ouverte 2.0; data downloaded on {_downloaded()}.", "",
             "## Manual-check entries", ""]
    found = 0
    checks = [(no, name, entries.get(no, {}).get("district_id") or district, answer)
              for no, name, district, answer in manual_checks()]

    parents = defaultdict(list)
    for m in _csv("memberships.csv"):
        if m["relation"] == "admin":
            parents[m["child_id"]].append(m["parent_id"])
    places = {p["id"]: p for p in _csv("places.csv")}
    unlocated = [pid for pid, p in places.items() if p["kind"] == "settlement" and p["geo_method"] == "unlocated"]
    queries = [(name, centres.get(district), 5) for _, name, district, _ in checks]
    queries += [(places.get(pid, {}).get("name_fr") or pid,
                 next((centres[t] for t in parents.get(pid, []) if t in centres), None), 3) for pid in unlocated]
    results = iter(search_all(idx, queries))

    for no, name, district, answer in checks:
        hits = next(results)
        rank = _answer_rank(hits, answer) if answer else None
        found += rank is not None
        lines.append(f"- {no} {name} ({district}) — by hand: {answer or '?'}; "
                     f"{f'rank {rank}' if rank else 'not in the top 5'}")
        lines.extend(f"  {i}. {_row(h)}" for i, h in enumerate(hits, 1))
    lines += ["", f"{found} of {len(checks)} hand-found answers in the top 5.", "", "## Places still unlocated", ""]
    for pid in unlocated:
        p = places.get(pid, {})
        hits = next(results)
        lines.append(f"- {pid}: {p.get('name_fr', '')}" + ("" if hits else " — no match"))
        lines.extend(f"  {i}. {_row(h)}" for i, h in enumerate(hits, 1))
    reviewed = load_rules().get("dicotopo_reviewed") or {}
    lines += [""] + review_settlements(idx, places, parents, centres, shared_points(dico), reviewed)
    for pid in sorted(set(reviewed) - set(places)):
        print(f"rules.yaml dicotopo_reviewed: no place {pid!r} (renamed?)")
    REVIEW_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"manual checks: {found} of {len(checks)} answers in the top 5; unlocated places: {len(unlocated)}")
    print(f"-> {REVIEW_FILE.relative_to(config.ROOT)}")
