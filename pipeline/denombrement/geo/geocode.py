"""Stage 5: coordinates and modern names for the settlements; label points for territories.

Every settlement Wikidata and GeoNames have in the region is matched locally against a
place's names (the index's name and the book's spellings), compared loosely (no article,
"Sainct" = "Saint", the scan's c/e and l/t confusions made equal). The index gives each
place an anchor: the commune of a hamlet, else the canton's chef-lieu. Candidates are scored
by name, class and distance to that anchor. A second pass uses the median of the other
located members of the place's district, for places without an anchor, matched ambiguously
or lying far from their district. Hamlets the databases lack are placed at their commune.

Output: data/curated/geocoding.csv, read by `make curate`; hand decisions
go in the `geocode` section of rules.yaml.
"""
from __future__ import annotations

import csv
import difflib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from denombrement import config
from denombrement.curate import build as curate
from denombrement.curate.build import _SUFFIX, fold
from denombrement.curate.build import name_key as _name_key
from denombrement.data.store import load_vocab
from denombrement.geo import geonames, wikidata

OUT_FILE = config.CURATED_DIR / "geocoding.csv"
# hist_map's geocoding (the bailliage d'Allemagne, checked by hand), copied into the cache: the
# container sees only this project. `cp ../hist_map/data/curated/geocoding.csv data/raw/geo_cache/hist_map_geocoding.csv`
HIST_MAP = config.RAW_DIR / "geo_cache" / "hist_map_geocoding.csv"
COLUMNS = ["place_id", "lat", "lon", "wikidata_id", "geonames_id", "name_fr", "name_de", "name_en", "name_ja", "country",
           "method", "confidence", "note"]

ANCHOR_KM = {"commune": 12.0, "canton": 25.0, "context": 30.0}
NAME_CUTOFF = 0.84         # loose-key similarity for a name match near an anchor
GLOBAL_CUTOFF = 0.92       # without an anchor
FAR_KM = 35.0              # a place this far from its district's other members is re-matched
_DIRECTIONS = re.compile(r"-(?:nord|sud|est|ouest|sud-est|sud-ouest|nord-est|nord-ouest|esl|nonl)\b.*$", re.I)


def name_key(name: str) -> str:
    """Stage 4's loose key, with this font's b/h confusion made equal too ("Robrbacb" = Rohrbach)."""
    return _name_key(name).replace("b", "h")


def label_keys(name: str) -> set[str]:
    """Keys for a database label and the base of a compound name ("Sierck-les-Bains" -> Sierck)."""
    return {k for k in (name_key(name), name_key(_SUFFIX.sub("", name))) if k}


BASE = "~"     # marks a key that is only the base of a compound name
SPELLING = "+"  # marks a key from the book's old spellings rather than the index's name
WEIGHTS = {"": 1.0, BASE: 0.9, SPELLING: 0.95, SPELLING + BASE: 0.85}


def place_keys(p: dict) -> set[str]:
    """A place's keys: its index name, then (marked) the book's spellings, which count a little
    less (entry 1516 is spelt "Budingen", but the index says Budange, not Buding/Büdingen)."""
    own = raw_keys(place_names({"name_fr": p["name_fr"]}))
    spellings = raw_keys(place_names({"name_fr": "", "variants": p.get("variants") or ""})) - own
    return own | {SPELLING + k for k in spellings if k.removeprefix(BASE) not in {o.removeprefix(BASE) for o in own}}


def raw_keys(names) -> set[str]:
    """Stage 4's loose keys (c/e, l/t) of names, without the b/h folding: for a village's own
    name that folding is too loose (Hénaménil is not Bénaménil). The base of a compound name is
    kept, marked, as a weaker key ("Charmes-sur-Moselle" -> "~charmes")."""
    out = set()
    for n in names:
        full, base = _name_key(n), _name_key(_SUFFIX.sub("", n))
        if full:
            out.add(full)
        if base and base != full:
            out.add(BASE + base)
    return out


def cand_keys(names) -> set[str]:
    """A database label's keys: its full name and, unmarked, the base of a compound name."""
    return {k for n in names for k in (_name_key(n), _name_key(_SUFFIX.sub("", n))) if k}


def clean_place_name(name: str) -> str:
    """An index canton or commune without OCR junk: "île Gorze" (de Gorze), "Fresnes-en-Voèvre(Meuse;, 1891"."""
    name = re.sub(r"\(.*$|,.*$", "", name)
    name = re.sub(r"^(?:[a-zîïé']{1,3}\s+)+", "", name.strip())  # stray lower-case words before the name
    return _DIRECTIONS.sub("", name).strip(" .;")


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


@dataclass
class Cand:
    source: str               # wikidata, geonames, hist_map
    lat: float
    lon: float
    keys: set[str]
    rank: float               # settlements above castles and abbeys above localities
    country: str | None
    qid: str | None = None
    geonameid: int | None = None
    fr: str | None = None
    de: str | None = None
    en: str | None = None
    ja: str | None = None
    raw: set[str] = field(default_factory=set)  # keys without the b/h folding, for a place's own name


class Gazetteer:
    """Candidates by loose name key and by 0.1° grid cell."""

    def __init__(self, items: dict[str, dict], gn: list[dict], seed: list[dict]):
        self.cands: list[Cand] = []
        for it in items.values():
            labels = [it[l] for l in ("fr", "de", "en") if it[l]]
            keys = {k for n in labels for k in label_keys(n)}
            rank = 3 if it["types"] & wikidata.SETTLEMENT_CLASSES else 2
            self.cands.append(Cand("wikidata", it["lat"], it["lon"], {k for k in keys if k}, rank, it["country"],
                                   qid=it["qid"], fr=it["fr"], de=it["de"], en=it["en"], ja=it["ja"],
                                   raw=cand_keys(labels)))
        for e in gn:
            rank = 2.5 if e["feature"].startswith("P.") else 1.5
            self.cands.append(Cand("geonames", e["lat"], e["lon"], {k for n in e["names"] for k in label_keys(n)}, rank,
                                   e["country"], geonameid=e["geonameid"], fr=e["name"], raw=cand_keys(e["names"])))
        for s in seed:
            self.cands.append(Cand("hist_map", s["lat"], s["lon"], label_keys(s["name_fr"]), 3.2, None,
                                   qid=s["wikidata_id"] or None, fr=s["name_fr"], de=s["name_de"] or None,
                                   en=s["name_en"] or None, raw=cand_keys([s["name_fr"]])))
        self.by_key: dict[str, list[Cand]] = defaultdict(list)
        self.grid: dict[tuple[int, int], list[Cand]] = defaultdict(list)
        for c in self.cands:
            for k in c.keys:
                self.by_key[k].append(c)
            self.grid[(int(c.lat * 10), int(c.lon * 10))].append(c)
        self.keys_by_initial: dict[str, list[str]] = defaultdict(list)
        for k in self.by_key:
            self.keys_by_initial[k[:2]].append(k)

    def near(self, point: tuple[float, float], radius_km: float) -> list[Cand]:
        r = int(radius_km / 7) + 1  # a 0.1° cell is 7-11 km here
        la, lo = int(point[0] * 10), int(point[1] * 10)
        out = []
        for i in range(la - r, la + r + 1):
            for j in range(lo - r, lo + r + 1):
                out.extend(c for c in self.grid.get((i, j), []) if km(point, (c.lat, c.lon)) <= radius_km)
        return out

    @staticmethod
    def sim(keys: set[str], c: Cand) -> float:
        """How well a place's raw keys fit a candidate's names. A key that is only the base of the
        place's compound name ("sexey" of Sexey-les-Bois) fits at 0.9: Sexey-aux-Forges has it too."""
        best = 0.0
        for k in keys:
            mark = k[:len(k) - len(k.lstrip(BASE + SPELLING))]
            weight = WEIGHTS.get(mark, 0.85)
            k = k[len(mark):]
            if k in c.raw:
                best = max(best, weight)
                continue
            for ck in c.raw:
                if ck[:1] == k[:1]:  # 'Ackerbach' is not 'Kerbach'
                    best = max(best, weight * difflib.SequenceMatcher(None, k, ck).ratio())
        return best

    def best_near(self, keys: set[str], point: tuple[float, float], radius: float,
                  cutoff: float = NAME_CUTOFF, exclude: frozenset = frozenset()) -> tuple[Cand, float, float] | None:
        """(candidate, similarity, km) for the best match near `point`, ignoring items in `exclude`."""
        scored = []
        for c in self.near(point, radius):
            if c.qid and c.qid in exclude:
                continue
            s = self.sim(keys, c)
            if s >= cutoff:
                d = km(point, (c.lat, c.lon))
                # The name counts most: an exact hamlet beats a neighbouring commune of a near name
                # (Budange, not Buding).
                scored.append((s * 4 + c.rank * 0.15 - d / radius * 0.5, c, s, d))
        if not scored:
            return None
        _, c, s, d = max(scored, key=lambda x: (x[0], tiebreak(x[1])))
        return c, s, d

    def exact(self, keys: set[str]) -> list[Cand]:
        return [c for k in sorted(keys) for c in self.by_key.get(k, [])]

    def fuzzy(self, keys: set[str], cutoff: float = GLOBAL_CUTOFF) -> list[tuple[Cand, float]]:
        out = []
        for k in sorted(keys):
            for hit in difflib.get_close_matches(k, self.keys_by_initial.get(k[:2], []), n=3, cutoff=cutoff):
                out.extend((c, difflib.SequenceMatcher(None, k, hit).ratio()) for c in self.by_key[hit])
        return out


@dataclass
class Result:
    place_id: str
    lat: float | None = None
    lon: float | None = None
    wikidata_id: str | None = None
    geonames_id: int | None = None
    name_fr: str | None = None
    name_de: str | None = None
    name_en: str | None = None
    name_ja: str | None = None
    country: str | None = None
    method: str = "unlocated"
    confidence: str = "low"
    note: str = ""
    anchor: tuple[float, float] | None = field(default=None, repr=False)
    fixed: bool = field(default=False, repr=False)     # set by a rule: the automatic passes leave it


def tiebreak(c: Cand) -> tuple:
    """A fixed order for equally good candidates: runs must give identical files."""
    return (c.rank, c.source, c.qid or "", c.geonameid or 0, c.lat, c.lon)


def place_names(p: dict) -> set[str]:
    """The place's names, split at "ou", "aliàs" and brackets."""
    names = {p["name_fr"], *[v for v in (p.get("variants") or "").split("|") if v]}
    out = set()
    for n in names:
        for part in re.split(r"\s+(?:ou|aliàs|alias|et)\s+|[()]", n):
            part = re.sub(r",.*$", "", part).strip(" .")
            if len(part) >= 3:
                out.add(part)
    return out


def take(res: Result, c: Cand, confidence: str, note: str) -> None:
    res.lat, res.lon = round(c.lat, 5), round(c.lon, 5)
    res.wikidata_id = c.qid
    res.geonames_id = c.geonameid
    res.name_de, res.name_en, res.name_ja = c.de, c.en, c.ja
    if c.source in ("wikidata", "hist_map") and c.fr and confidence != "low":
        res.name_fr = c.fr  # a reliable match gives the modern spelling; else the index's stays
    res.country = c.country or res.country
    res.method = c.source
    res.confidence, res.note = confidence, note


def run() -> dict[str, Result]:
    vocab = load_vocab(config.CURATED_DIR / "vocab.yaml")
    rules = (curate.load_rules().get("geocode") or {})
    built = curate.build()
    places = built.places
    memberships = built.memberships

    print("loading Wikidata (region, cached by tile) ...")
    items = wikidata.region()
    print(f"  {len(items)} items")
    print("loading GeoNames dumps (FR, DE, LU) ...")
    gn = geonames.region()
    print(f"  {len(gn)} entries")
    seed = list(csv.DictReader(HIST_MAP.open())) if HIST_MAP.exists() else []
    seed = [s for s in seed if s.get("lat") and s.get("method") not in ("approximate", "unlocated", "territory")]
    for s in seed:
        s["lat"], s["lon"] = float(s["lat"]), float(s["lon"])
    print(f"  {len(seed)} located places from hist_map")
    gaz = Gazetteer(items, gn, seed)

    anchors: dict[str, tuple[float, float] | None] = {}

    def locate(name: str, near: tuple[float, float] | None = None) -> tuple[float, float] | None:
        """A commune or canton seat the index names."""
        key = (name, near)
        if key in anchors:
            return anchors[key]
        keys = {name_key(clean_place_name(name))} - {""}
        if not keys:
            anchors[key] = None
            return None
        cands = [c for c in gaz.exact(keys) if c.rank >= 2.5]
        if not cands:
            cands = [c for c, s in gaz.fuzzy(keys, 0.85) if c.rank >= 2.5]
        if near:
            cands = [c for c in cands if km(near, (c.lat, c.lon)) <= 30] or []
            cands.sort(key=lambda c: (km(near, (c.lat, c.lon)), tiebreak(c)))
        else:
            cands.sort(key=tiebreak, reverse=True)
        anchors[key] = (cands[0].lat, cands[0].lon) if cands else None
        return anchors[key]

    def seats(name: str) -> list[tuple[float, float]]:
        """Every commune or canton seat of that name."""
        keys = {name_key(clean_place_name(name))} - {""}
        cands = [c for c in gaz.exact(keys) if c.rank >= 2.5]
        # a commune merged since ("Thiaucourt" is Thiaucourt-Regniéville)
        cands += [c for k in keys for hit in gaz.keys_by_initial.get(k[:2], []) if hit.startswith(k) and len(hit) > len(k) + 3
                  for c in gaz.by_key[hit] if c.rank >= 2.5]
        cands = cands or [c for c, s in gaz.fuzzy(keys, 0.85) if c.rank >= 2.5]
        return sorted({(c.lat, c.lon) for c in cands})

    results: dict[str, Result] = {}
    for pid, p in places.items():
        if p["kind"] != "settlement":
            continue
        res = Result(pid, name_fr=p["name_fr"], country=p.get("modern_country") or None)
        results[pid] = res
        rule = rules.get(pid)
        if rule and ("lat" in rule or "wikidata" in rule or rule.get("unlocated") or "approximate" in rule):
            continue  # applied after the automatic passes
        keys = place_keys(p)
        canton = locate(p["index_canton"]) if p.get("index_canton") else None
        commune = locate(p["index_commune"], canton) if p.get("index_commune") else None
        res.anchor = commune or canton
        if commune or canton:
            kind = "commune" if commune else "canton"
            hit = gaz.best_near(keys, res.anchor, ANCHOR_KM[kind])
            if hit:
                c, s, d = hit
                take(res, c, "high" if s >= 0.95 else "medium", f"{s:.2f} near the index's {kind} ({d:.0f} km)")
                continue
            if commune:
                res.lat, res.lon = round(commune[0], 5), round(commune[1], 5)
                res.method, res.confidence = "approximate", "low"
                res.note = f"not in Wikidata/GeoNames; placed at its commune {p['index_commune']}"
                continue
            if any(difflib.SequenceMatcher(None, k, name_key(clean_place_name(p["index_canton"]))).ratio() >= 0.85
                   for k in keys):
                res.lat, res.lon = round(canton[0], 5), round(canton[1], 5)
                res.method, res.confidence, res.note = "canton", "medium", "the chef-lieu of its canton"
                continue
        # No anchor: an exact name, unambiguous in the region.
        exact = [c for c in gaz.exact({name_key(n) for n in place_names(p)} - {""}) if c.rank >= 2.5
                 and gaz.sim(keys, c) >= 0.95]
        spots = {(round(c.lat, 2), round(c.lon, 2)) for c in exact}
        if exact and len({(round(a, 1), round(b, 1)) for a, b in spots}) == 1:
            take(res, max(exact, key=tiebreak), "medium", "exact name, no anchor")
        elif exact:
            take(res, max(exact, key=tiebreak), "low", f"ambiguous without an anchor ({len(spots)} spots)")

    _apply_rules(results, rules, items)   # first, so that the passes below leave these alone
    _refine(results, places, memberships, gaz, locate)
    _one_place_per_item(results, places, gaz)
    _check_index(results, places, gaz, seats, rules, memberships)
    _apply_rules(results, rules, items)

    # Territories: a label point at the seat (a settlement of the seat's name in the territory),
    # else at the centre of their located members; Japanese names from the seat.
    children: dict[str, list[str]] = defaultdict(list)
    for m in memberships:
        children[m["parent_id"]].append(m["child_id"])

    def members(tid: str, seen: frozenset = frozenset()) -> list[str]:
        out = []
        for c in children.get(tid, []):
            if c in results:
                out.append(c)
            elif c not in seen:
                out += members(c, seen | {tid})
        return out

    for pid, p in places.items():
        if p["kind"] != "territory":
            continue
        seat = re.sub(r"^.*?\b(?:de la|de|d'|du|des)\s*", "", p["name_fr"], count=1) if " " in p["name_fr"] else p["name_fr"]
        mem = [m for m in members(pid) if results[m].lat is not None]
        seat_res = next((results[m] for m in mem if name_key(results[m].name_fr or "") == name_key(seat.split(" et ")[0])
                         or name_key(places[m]["name_fr"]) == name_key(seat.split(" et ")[0])), None)
        res = Result(pid, name_fr=p["name_fr"], method="territory", confidence="medium")
        if seat_res:
            res.lat, res.lon, res.note = seat_res.lat, seat_res.lon, f"seat: {seat_res.place_id}"
        elif mem:
            res.lat = round(sum(results[m].lat for m in mem) / len(mem), 5)
            res.lon = round(sum(results[m].lon for m in mem) / len(mem), 5)
            res.note = f"centre of {len(mem)} located member(s)"
        else:
            res.note = "no seat or located members"
        type_ja = vocab["territory_types"].get(p["place_type"], {}).get("ja", "")
        seat_ja = seat_res.name_ja if seat_res and seat_res.name_ja else None
        res.name_ja = f"{seat_ja}{type_ja}" if seat_ja else None
        results[pid] = res

    _write(results)
    settlements = [r for r in results.values() if r.method != "territory"]
    located = sum(r.lat is not None for r in settlements)
    print(f"settlements located: {located}/{len(settlements)} ({100 * located / max(1, len(settlements)):.1f}%)")
    for (method, conf), n in sorted(Counter((r.method, r.confidence) for r in settlements).items()):
        print(f"  {method:12} {conf:6} {n}")
    terr = [r for r in results.values() if r.method == "territory"]
    print(f"territories: {len(terr)}, with a label point: {sum(r.lat is not None for r in terr)}")
    return results


def _refine(results: dict[str, Result], places: dict, memberships: list[dict], gaz: Gazetteer, locate) -> None:
    """Second pass: the median of the other located members of a place's districts."""
    parents: dict[str, set[str]] = defaultdict(set)
    members: dict[str, list[str]] = defaultdict(list)
    for m in memberships:
        if m["relation"] == "admin":
            parents[m["child_id"]].add(m["parent_id"])
            members[m["parent_id"]].append(m["child_id"])
    reliable = {pid for pid, r in results.items() if r.lat is not None and r.confidence != "low"}

    def centre(tid: str, exclude: str):
        if places.get(tid, {}).get("place_type") in ("bailiwick", "duchy"):
            return None  # too large to say where a member is
        pts = [(results[c].lat, results[c].lon) for c in members.get(tid, []) if c in reliable and c != exclude]
        if len(pts) < 3:
            return None
        lats, lons = sorted(a for a, _ in pts), sorted(b for _, b in pts)
        return lats[len(lats) // 2], lons[len(lons) // 2]

    changed = flagged = 0
    for pid, res in results.items():
        if res.fixed:
            continue
        centres = [c for t in parents.get(pid, ()) if (c := centre(t, pid))]
        if not centres:
            continue
        context = (sum(a for a, _ in centres) / len(centres), sum(b for _, b in centres) / len(centres))
        far = res.lat is None or km(context, (res.lat, res.lon)) > FAR_KM
        weak = res.confidence == "low" or "no anchor" in res.note
        if not (far or weak):
            continue
        if "near the index's" in res.note and res.confidence == "high":
            # The editor's commune or canton says where it is, and the name fits it well: the
            # district doesn't move it. (A canton's name can be ambiguous: a loose match near
            # the wrong Saint-Nicolas gives way to the district.)
            if far:
                res.note += f"; {km(context, (res.lat, res.lon)):.0f} km from its district"
                flagged += 1
            continue
        p = places[pid]
        if res.method == "approximate" and far and p.get("index_commune"):
            # Placed at the wrong namesake of its commune (Rupt-en-Woëvre for Rupt-sur-Moselle):
            # the commune near the district instead.
            commune = locate(p["index_commune"], context)
            if commune:
                res.lat, res.lon = round(commune[0], 5), round(commune[1], 5)
                res.note = f"not in Wikidata/GeoNames; placed at its commune {p['index_commune']} (near its district)"
                changed += 1
                continue
        keys = place_keys(p)
        # Short names have many near neighbours: they must match almost exactly.
        cutoff = 0.95 if min((len(k.lstrip(BASE + SPELLING)) for k in keys), default=0) < 7 else 0.86
        hit = gaz.best_near(keys, context, ANCHOR_KM["context"], cutoff=cutoff)
        if hit and (far or res.method == "approximate" or hit[0].qid != res.wikidata_id):
            c, s, d = hit
            take(res, c, "medium" if s >= 0.95 else "low", f"{s:.2f} near its district's other members ({d:.0f} km)")
            changed += 1
        elif hit:
            res.confidence = "medium" if res.confidence == "low" and hit[1] >= 0.95 else res.confidence
        elif far and res.lat is not None:
            # A match on the index's own canton or commune stands: fiefs can lie far from the
            # prévôté they owe homage to. Anything else that far is doubtful.
            if "near the index's" not in res.note:
                res.confidence = "low"
            res.note = (res.note + "; " if res.note else "") + f"{km(context, (res.lat, res.lon)):.0f} km from its district"
            flagged += 1
    print(f"district context: {changed} place(s) re-matched, {flagged} flagged as far from their district")


def _district_context(results: dict[str, Result], places: dict, memberships: list[dict]) -> dict[str, tuple]:
    """Each settlement's district context: the median of the other reliably located members of its
    districts, for choosing among namesakes (a bailliage will do for that)."""
    parents: dict[str, set[str]] = defaultdict(set)
    members: dict[str, list[str]] = defaultdict(list)
    for m in memberships:
        if m["relation"] == "admin":
            parents[m["child_id"]].add(m["parent_id"])
            members[m["parent_id"]].append(m["child_id"])
    reliable = {pid for pid, r in results.items() if r.lat is not None and r.confidence != "low"}
    out = {}
    for pid in results:
        centres = []
        for t in parents.get(pid, ()):
            if places.get(t, {}).get("place_type") == "duchy":
                continue
            pts = [(results[c].lat, results[c].lon) for c in members.get(t, []) if c in reliable and c != pid]
            if len(pts) >= 3:
                lats, lons = sorted(a for a, _ in pts), sorted(b for _, b in pts)
                centres.append((lats[len(lats) // 2], lons[len(lons) // 2]))
        if centres:
            out[pid] = (sum(a for a, _ in centres) / len(centres), sum(b for _, b in centres) / len(centres))
    return out


def _check_index(results: dict[str, Result], places: dict, gaz: Gazetteer, seats, rules: dict,
                 memberships: list[dict]) -> None:
    """Last: every place where the index names its commune or canton must lie there. Names
    repeat (two Berschweilers, three Colombeys): the one nearest the place's district is meant,
    else the one nearest the match. A match far from it is made again near it, or marked doubtful."""
    context = _district_context(results, places, memberships)
    moved = flagged = missing = 0
    for pid, res in results.items():
        p = places[pid]
        if pid in rules or not (p.get("index_commune") or p.get("index_canton")):
            continue
        kind = "commune" if p.get("index_commune") else "canton"
        where = p.get("index_commune") or p.get("index_canton")
        pts = seats(where)
        if not pts:
            res.note = (res.note + "; " if res.note else "") + f"the index's {kind} {where} is not found"
            missing += 1
            continue
        if res.lat is None:
            continue
        if pid in context and len(pts) > 1:
            anchor = min(pts, key=lambda pt: km(pt, context[pid]))
            if km(anchor, context[pid]) > FAR_KM:     # no seat of that name near the district
                anchor = min(pts, key=lambda pt: km(pt, (res.lat, res.lon)))
        else:
            anchor = min(pts, key=lambda pt: km(pt, (res.lat, res.lon)))
        d = km(anchor, (res.lat, res.lon))
        if d <= ANCHOR_KM[kind]:
            continue
        hit = gaz.best_near(place_keys(p), anchor, ANCHOR_KM[kind])
        if hit:
            c, s, dd = hit
            take(res, c, "high" if s >= 0.95 else "medium",
                 f"{s:.2f} near the index's {kind} ({dd:.0f} km); was {d:.0f} km away")
            moved += 1
        else:
            res.confidence = "low"
            res.note = (res.note + "; " if res.note else "") + f"{d:.0f} km from the index's {kind} {where}"
            flagged += 1
    print(f"index check: {moved} place(s) matched again near the index's commune or canton, {flagged} flagged, "
          f"{missing} with a commune or canton not found")


def _one_place_per_item(results: dict[str, Result], places: dict, gaz: Gazetteer) -> None:
    """Two places matched to one Wikidata item: the one whose name fits it best keeps it. The
    other keeps it too when both are the same place (the same name, or the same canton in the
    index: two index lines for one village); otherwise it looks again without that item."""
    by_qid: dict[str, list[str]] = defaultdict(list)
    for pid, r in results.items():
        if r.wikidata_id and r.lat is not None:
            by_qid[r.wikidata_id].append(pid)
    taken = frozenset(by_qid)
    moved = 0
    for qid, pids in sorted(by_qid.items()):
        if len(pids) < 2:
            continue
        cand = next((c for c in gaz.cands if c.qid == qid), None)
        if cand is None:
            continue
        fit = {pid: gaz.sim(place_keys(places[pid]), cand) for pid in pids}
        winner = max(sorted(pids), key=lambda pid: (results[pid].fixed, fit[pid],
                                                    {"high": 2, "medium": 1}.get(results[pid].confidence, 0)))
        for pid in sorted(pids):
            if pid == winner or results[pid].fixed:
                continue
            same_canton = places[pid].get("index_canton") and \
                name_key(places[pid]["index_canton"]) == name_key(places[winner].get("index_canton") or "")
            same_name = difflib.SequenceMatcher(None, name_key(places[pid]["name_fr"]),
                                                name_key(places[winner]["name_fr"])).ratio() >= 0.9
            if fit[pid] >= 0.95 and same_canton and same_name:
                continue  # the same village twice in the index: curate merges them
            res = results[pid]
            point = res.anchor or (res.lat, res.lon)
            hit = gaz.best_near(place_keys(places[pid]), point, ANCHOR_KM["canton"], exclude=taken)
            if hit:
                take(res, hit[0], "medium" if hit[1] >= 0.95 else "low",
                     f"{hit[1]:.2f}; {qid} went to {winner}, whose name fits it better")
            else:
                res.lat = res.lon = res.wikidata_id = None
                res.method, res.confidence = "unlocated", "low"
                res.note = f"its match {qid} went to {winner}, whose name fits it better"
            moved += 1
    print(f"one place per item: {moved} place(s) moved off a shared Wikidata item")


def _apply_rules(results: dict[str, Result], rules: dict, items: dict) -> None:
    """rules.yaml `geocode`: {place: {wikidata: Q…}|{lat, lon}|{approximate: other-place}|{unlocated: true}, note}."""
    for pid, rule in rules.items():
        res = results.get(pid)
        if res is None:
            continue
        note = rule.get("note", "set in rules.yaml")
        res.fixed = True
        if "wikidata" in rule and rule["wikidata"] in items:
            it = items[rule["wikidata"]]
            res.lat, res.lon, res.wikidata_id = round(it["lat"], 5), round(it["lon"], 5), it["qid"]
            res.name_fr, res.name_de, res.name_en, res.name_ja = it["fr"] or res.name_fr, it["de"], it["en"], it["ja"]
            res.country, res.method, res.confidence, res.note = it["country"], "rule", "high", note
        elif "lat" in rule:
            res.lat, res.lon, res.method, res.confidence, res.note = rule["lat"], rule["lon"], "rule", "high", note
        elif "approximate" in rule and results.get(rule["approximate"]) and results[rule["approximate"]].lat:
            t = results[rule["approximate"]]
            res.lat, res.lon, res.method, res.confidence, res.note = t.lat, t.lon, "approximate", "low", note
        elif rule.get("unlocated"):
            res.lat = res.lon = None
            res.method, res.confidence, res.note = "unlocated", "low", note
        for lang in ("fr", "de", "en"):
            if rule.get(f"name_{lang}"):
                setattr(res, f"name_{lang}", rule[f"name_{lang}"])


def _write(results: dict[str, Result]) -> None:
    with OUT_FILE.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in sorted(results.values(), key=lambda r: r.place_id):
            w.writerow({c: ("" if getattr(r, c) is None else getattr(r, c)) for c in COLUMNS})
