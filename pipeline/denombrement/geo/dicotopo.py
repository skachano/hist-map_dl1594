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
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

import requests

from denombrement import config
from denombrement.curate.build import fold
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


def _sub(a: str, b: str) -> float:
    return 0.0 if a == b else _CHEAP if frozenset((a, b)) in _PAIRS else 1.0


def ocr_distance(a: str, b: str) -> float:
    """Weighted Levenshtein between two spelling keys."""
    n, m = len(a), len(b)
    d = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = float(i)
    for j in range(1, m + 1):
        d[0][j] = float(j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + _sub(a[i - 1], b[j - 1]))
            for x, y in _MULTI:
                if i >= len(x) and j >= len(y) and a[i - len(x):i] == x and b[j - len(y):j] == y:
                    best = min(best, d[i - len(x)][j - len(y)] + _CHEAP)
            d[i][j] = best
    return d[n][m]


_COARSE = str.maketrans("eoauictbhfsnmrjyvq", "eeeeiilhhssnnnilug")


def coarse(key: str) -> str:
    """A key with the confusable letters merged, for a quick first sift."""
    for x, y in (("fl", "h"), ("li", "h"), ("rn", "m"), ("ii", "u"), ("cl", "d")):
        key = key.replace(x, y)
    return key.translate(_COARSE)


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
        for p in places:
            p["kind"] = kind(p)
            for name, year in [(p["label"], ""), *old_labels(p)]:
                for part in re.split(r"\s+ou\s+", name):  # "Aboncourt ou Aboncourt-sur-Seille"
                    k = spelling_key(re.sub(r"\s*\(.*?\)", "", part))  # "Corps-Mort (Chemin du)"
                    if len(k) >= 3:
                        self.labels[k].append((p, part, year))
                        self.coarse[k] = coarse(k)

    def search(self, name: str, near: tuple[float, float] | None = None, limit: int = 5) -> list[Hit]:
        best: dict[str, Hit] = {}
        for qk, weight in query_keys(name):
            sift = difflib.SequenceMatcher(None, "", coarse(qk))
            for k, refs in self.labels.items():
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
    """Median of each district's located members."""
    located = {r["place_id"]: (float(r["lat"]), float(r["lon"])) for r in _csv("geocoding.csv")
               if r["lat"] and r["confidence"] != "low"}
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


def run() -> None:
    idx = Index(region())
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
    unlocated = [r["place_id"] for r in _csv("geocoding.csv") if r["method"] == "unlocated"]
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
    REVIEW_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"manual checks: {found} of {len(checks)} answers in the top 5; unlocated places: {len(unlocated)}")
    print(f"-> {REVIEW_FILE.relative_to(config.ROOT)}")
