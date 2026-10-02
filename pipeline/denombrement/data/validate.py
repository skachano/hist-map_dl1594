"""Integrity checks for the curated dataset (doc/Plan.md §2)."""
from __future__ import annotations

from collections import defaultdict

from denombrement.data.models import LAST_ENTRY, entry_number, share_value
from denombrement.data.store import LANGS, Dataset, Issue

DUCHY = "duchy-lorraine"  # the root of the administrative hierarchy (a place) and the duke (an entity)
FACT_TABLES = ("entries", "memberships", "holdings")  # rows that must cite a page


def validate(ds: Dataset) -> list[Issue]:
    issues = list(ds.issues)

    def err(table, row, msg):
        issues.append(Issue("error", table, row, msg))

    def warn(table, row, msg):
        issues.append(Issue("warning", table, row, msg))

    def info(table, row, msg):
        issues.append(Issue("info", table, row, msg))

    _check_vocab(ds, err)
    places = {p.id: p for _, p in ds.places}
    place_ids = _unique(ds.places, "places", lambda p: p.id, err)
    entity_ids = _unique(ds.entities, "entities", lambda e: e.id, err)
    _unique(ds.features, "features", lambda f: f.id, err)
    entry_nos = _unique(ds.entries, "entries", lambda e: e.no, err)

    def fk(table, line, fld, value, ids, target):
        if value is not None and value not in ids:
            err(table, line, f"{fld} '{value}' not found in {target}")

    for table in FACT_TABLES:
        for line, row in getattr(ds, table):
            if not row.source_page:
                err(table, line, "source_page is required for facts")

    _check_places(ds, places, entity_ids, fk, err, warn, info)
    _check_entries(ds, places, place_ids, entity_ids, fk, err, warn, info)
    _check_memberships(ds, places, place_ids, fk, err, warn, info)
    for line, h in ds.holdings:
        fk("holdings", line, "place_id", h.place_id, place_ids, "places")
        fk("holdings", line, "holder_id", h.holder_id, entity_ids, "entities")
        for other in h.share_with:
            fk("holdings", line, "share_with", other, entity_ids, "entities")
        for no in h.via_entry:
            fk("holdings", line, "via_entry", no, entry_nos, "entries")
        if h.tenure == "domain" and h.holder_id not in (None, DUCHY):
            warn("holdings", line, f"domain held by '{h.holder_id}': the domain is the duke's")
    _check_shares(ds, err)
    for line, f in ds.features:
        fk("features", line, "place_id", f.place_id, place_ids, "places")
    return issues


def _check_vocab(ds: Dataset, err) -> None:
    for vocab_name, terms in ds.vocab.items():
        for key, labels in terms.items():
            missing = [lang for lang in LANGS if not labels.get(lang)]
            if missing:
                err("vocab", None, f"{vocab_name}.{key} lacks labels: {missing}")
    for key, labels in ds.vocab.get("territory_types", {}).items():
        if labels.get("hierarchy") not in ("admin", "feudal"):
            err("vocab", None, f"territory_types.{key} needs hierarchy: admin or feudal")
    for table in ("entries", "places", "memberships", "entities", "holdings", "features"):
        for line, row in getattr(ds, table):
            for fld, vocab_name in row.vocab_fields.items():
                value = getattr(row, fld)
                for v in value if isinstance(value, list) else [value]:
                    if v is not None and v not in ds.vocab.get(vocab_name, {}):
                        err(table, line, f"{fld} '{v}' is not in vocab.{vocab_name}")


def _unique(rows, table, key, err) -> set[str]:
    seen: dict[str, int] = {}
    for line, row in rows:
        k = key(row)
        if k in seen:
            err(table, line, f"duplicate id '{k}' (first on line {seen[k]})")
        seen.setdefault(k, line)
    return set(seen)


def seat(p) -> str:
    """The seat part of a territory id: "provostship-deneuvre" -> "deneuvre"."""
    prefix = "temporality-abbey-" if p.place_type == "temporality" else p.place_type.replace("_", "-") + "-"
    return p.id[len(prefix):] if p.id.startswith(prefix) else p.id


def _check_places(ds: Dataset, places, entity_ids, fk, err, warn, info) -> None:
    ttypes = ds.vocab.get("territory_types", {})
    for line, p in ds.places:
        if (p.lat is None) != (p.lon is None):
            err("places", line, "lat and lon must be given together")
        if p.kind == "settlement":
            if p.place_type not in ds.vocab.get("place_types", {}):
                err("places", line, f"place_type '{p.place_type}' is not in vocab.place_types")
            continue
        # Territories.
        if p.place_type not in ttypes:
            err("places", line, f"place_type '{p.place_type}' is not in vocab.territory_types")
        elif p.hierarchy != ttypes[p.place_type].get("hierarchy"):
            err("places", line, f"a {p.place_type} is {ttypes[p.place_type].get('hierarchy')}, "
                                f"but hierarchy is {p.hierarchy}")
        if p.id == seat(p) and p.id != DUCHY:
            warn("places", line, f"territory id should be '{p.place_type}-<seat>'")
        if p.holder_id:
            for holder in p.holder_id:
                fk("places", line, "holder_id", holder, entity_ids, "entities")
            if p.hierarchy == "admin":
                err("places", line, "an administrative division has no holder (its counterpart realm does)")
        elif p.hierarchy == "feudal":
            info("places", line, f"realm '{p.id}' has no holder")
        if p.counterpart_id:
            other = places.get(p.counterpart_id)
            if other is None:
                err("places", line, f"counterpart_id '{p.counterpart_id}' not found in places")
                continue
            if other.counterpart_id != p.id:
                err("places", line, f"counterpart '{other.id}' does not point back")
            if other.kind != "territory" or other.hierarchy == p.hierarchy:
                err("places", line, f"counterpart '{other.id}' must be a territory of the other hierarchy")
            if seat(other) != seat(p):
                warn("places", line, f"counterpart '{other.id}' has another seat")
            if not p.counterpart_basis:
                err("places", line, "counterpart_basis is required with counterpart_id")


def _check_entries(ds: Dataset, places, place_ids, entity_ids, fk, err, warn, info) -> None:
    links = {(m.child_id, m.parent_id, m.relation) for _, m in ds.memberships}
    previous: int | None = None
    numbers: list[int] = []
    for line, e in ds.entries:
        n = entry_number(e.no)
        if n is not None:
            if not 1 <= n <= LAST_ENTRY:
                err("entries", line, f"entry number {n} is outside 1-{LAST_ENTRY}")
            if previous is not None and n <= previous:
                warn("entries", line, f"entry {n} comes after {previous}: out of sequence")
            previous = n
            numbers.append(n)
        fk("entries", line, "place_id", e.place_id, place_ids, "places")
        for fld, want in (("district_id", "admin"), ("realm_id", "feudal")):
            value = getattr(e, fld)
            fk("entries", line, fld, value, place_ids, "places")
            if value in places and places[value].hierarchy != want:
                err("entries", line, f"{fld} '{value}' is not a{'n administrative' if want == 'admin' else ' feudal'} "
                                     "territory")
        for fld in ("holder_id", "share_with"):
            for value in getattr(e, fld):
                fk("entries", line, fld, value, entity_ids, "entities")
        if e.series == "main":
            if not e.district_id:
                err("entries", line, "an entry of the Dénombrement needs its district")
            if not e.section:
                err("entries", line, "an entry of the Dénombrement needs its section")
        if e.share_with and not e.share:
            warn("entries", line, "share_with is given without a share")
        # The entry's district and realm should be mirrored by the place's memberships.
        if e.place_id and e.series == "main":
            if e.district_id and (e.place_id, e.district_id, "admin") not in links:
                warn("entries", line, f"no admin membership {e.place_id} -> {e.district_id}")
            if e.realm_id and (e.place_id, e.realm_id, "feudal") not in links:
                warn("entries", line, f"no feudal membership {e.place_id} -> {e.realm_id}")
    if numbers:
        missing = sorted(set(range(min(numbers), max(numbers) + 1)) - set(numbers))
        if missing:
            shown = ", ".join(map(str, missing[:20])) + (" …" if len(missing) > 20 else "")
            info("entries", None, f"{len(missing)} numbers missing between {min(numbers)} and {max(numbers)}: {shown}")


def _check_memberships(ds: Dataset, places, place_ids, fk, err, warn, info) -> None:
    seen: dict[tuple[str, str, str], int] = {}
    for line, m in ds.memberships:
        fk("memberships", line, "child_id", m.child_id, place_ids, "places")
        fk("memberships", line, "parent_id", m.parent_id, place_ids, "places")
        key = (m.child_id, m.parent_id, m.relation)
        if key in seen:
            warn("memberships", line, f"duplicates line {seen[key]}")
        seen.setdefault(key, line)
        child, parent = places.get(m.child_id), places.get(m.parent_id)
        if not child or not parent:
            continue
        if parent.kind != "territory":
            err("memberships", line, f"parent '{parent.id}' is not a territory")
            continue
        if m.relation == "admin":
            if parent.hierarchy != "admin" or (child.kind == "territory" and child.hierarchy != "admin"):
                err("memberships", line, "an admin link joins administrative divisions (and settlements)")
        elif m.relation == "feudal":
            if parent.hierarchy != "feudal" or (child.kind == "territory" and child.hierarchy != "feudal"):
                err("memberships", line, "a feudal link joins feudal realms (and settlements)")
        elif m.relation == "ressort":
            if child.hierarchy != "feudal" or parent.hierarchy != "admin":
                err("memberships", line, "a ressort link goes from a feudal realm to an administrative division")
            elif child.counterpart_id and child.counterpart_id != parent.id:
                warn("memberships", line, f"realm '{child.id}' has a counterpart; its ressort should be "
                                          f"'{child.counterpart_id}'")

    parents: dict[str, set[str]] = defaultdict(set)
    for _, m in ds.memberships:
        parents[m.child_id].add(m.parent_id)

    # Cycles, over all links.
    def reaches(start: str, target: str, seen: set[str]) -> bool:
        for p in parents.get(start, ()):
            if p == target or (p not in seen and reaches(p, target, seen | {p})):
                return True
        return False

    cyclic = set()
    for line, m in ds.memberships:
        if m.child_id == m.parent_id or reaches(m.parent_id, m.child_id, {m.parent_id}):
            err("memberships", line, f"membership cycle through '{m.child_id}'")
            cyclic.add(m.child_id)

    # Every settlement and administrative division reaches the duchy: through admin links, or
    # through a realm's ressort.
    def to_duchy(pid: str, seen: frozenset = frozenset()) -> bool:
        if pid == DUCHY:
            return True
        return any(p not in seen and to_duchy(p, seen | {pid}) for p in parents.get(pid, ()))

    lines = {p.id: line for line, p in ds.places}
    # Places named only in the thematic lists (the abbeys of Metz and Toul…) need not be in the duchy.
    in_main = {e.place_id for _, e in ds.entries if e.series == "main"}
    in_lists = {e.place_id for _, e in ds.entries if e.series != "main"}
    for p in places.values():
        if p.id == DUCHY or p.id in cyclic or (p.kind == "territory" and p.hierarchy == "feudal"):
            continue
        if p.kind == "settlement" and p.id in in_lists - in_main and not parents.get(p.id):
            info("places", lines[p.id], f"'{p.id}' is only in the thematic lists")
            continue
        if not to_duchy(p.id):
            err("places", lines[p.id], f"'{p.id}' does not reach the duchy through its memberships")
    for p in places.values():
        if p.kind == "territory" and p.hierarchy == "feudal" and p.id not in cyclic and not to_duchy(p.id):
            warn("places", lines[p.id], f"realm '{p.id}' has no ressort or parent in the duchy")

    # Counterparts: report member sets that differ.
    members: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, m in ds.memberships:
        if m.relation in ("admin", "feudal") and places.get(m.child_id) and places[m.child_id].kind == "settlement":
            members[(m.parent_id, m.relation)].add(m.child_id)
    for line, p in ds.places:
        if p.counterpart_id and p.hierarchy == "admin" and p.counterpart_id in places:
            division = members[(p.id, "admin")]
            realm = members[(p.counterpart_id, "feudal")]
            if division != realm:
                only_d, only_r = sorted(division - realm), sorted(realm - division)
                info("places", line, f"counterparts '{p.id}' and '{p.counterpart_id}' differ: "
                                     f"{len(only_d)} only in the division {only_d[:5]}, "
                                     f"{len(only_r)} only in the realm {only_r[:5]}")


def _check_shares(ds: Dataset, err) -> None:
    by_place: dict[str, list[tuple[int, object]]] = defaultdict(list)
    for line, h in ds.holdings:
        by_place[h.place_id].append((line, h))
    for place, rows in by_place.items():
        total = sum((share_value(h.share) or 0) for _, h in rows)
        if total > 1:
            err("holdings", rows[-1][0], f"shares at {place} add up to {total}")


def coverage(ds: Dataset) -> list[str]:
    settlements = [p for _, p in ds.places if p.kind == "settlement"]
    territories = [p for _, p in ds.places if p.kind == "territory"]
    main = [e for _, e in ds.entries if e.series == "main"]
    located = [p for p in settlements if p.lat is not None]
    with_place = [e for _, e in ds.entries if e.place_id]
    return [
        f"entries: {len(ds.entries)} ({len(main)} in the Dénombrement), places: {len(ds.places)} "
        f"({len(settlements)} settlements, {sum(t.hierarchy == 'admin' for t in territories)} divisions, "
        f"{sum(t.hierarchy == 'feudal' for t in territories)} realms), memberships: {len(ds.memberships)}, "
        f"entities: {len(ds.entities)}, holdings: {len(ds.holdings)}, features: {len(ds.features)}",
        f"entries with a place: {len(with_place)}/{len(ds.entries)}; settlements geocoded: "
        f"{len(located)}/{len(settlements)}; counterpart pairs: "
        f"{sum(1 for t in territories if t.counterpart_id and t.hierarchy == 'admin')}",
    ]
