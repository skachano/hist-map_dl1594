"""Stage 6: territory areas derived from settlement points.

1. Each located settlement gets a Voronoi cell (the land nearer to it than to any other
   settlement), clipped to CLIP_KM around the settlements so outlying villages don't claim
   empty land. As in hist_map, only the book's places divide the land, except in the foreign
   lands of manual/foreign_lands.csv (Metz, Toul and Verdun with their countrysides, the bishops'
   towns, Nassau-Saarbrücken): there, the Wikidata communes the book doesn't list are neutral
   seed points, with cells of their own that belong to no territory, so Lorraine's villages
   don't cover the enclaves. (Unlisted communes elsewhere, like the Warndt's, are not foreign.)
2. A territory's area is the union of its settlements' cells, following the links of its own
   hierarchy: administrative divisions through `admin` links (village -> ban -> prévôté ->
   bailliage), feudal realms through `feudal` links. Divisions tile the duchy; realms cover only
   their members, so the land between them stays empty.
3. A settlement in two divisions ("en partie", listed under two prévôtés, or the seat of a ban
   listed in its prévôté) is in both, as in hist_map: its cell is in both areas, which overlap
   there, and both list it as `shared` (the app hatches it).
4. Places placed only approximately (a hamlet at its commune) or doubtfully add no land; they
   stay members and keep their points.

These areas are approximations: the book gives members, not boundaries.

Output: data/geometry/cells.geojson and data/geometry/territories.geojson.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict

import shapely
from pyproj import Transformer
from shapely.geometry import MultiPoint, Point, mapping, shape
from shapely.ops import transform, unary_union

from denombrement import config
from denombrement.curate.build import load_rules
from denombrement.data import store
from denombrement.geo import wikidata
from denombrement.geo.geocode import label_keys, name_key

OUT_DIR = config.DATA_DIR / "geometry"
CLIP_KM = 6.0           # how far a settlement's cell may reach
NEUTRAL_MIN_KM = 1.5    # a Wikidata commune this close to a listed settlement is that settlement
FOREIGN_LANDS = config.CURATED_DIR / "manual" / "foreign_lands.csv"
# The Territories view's administrative levels, by kind of division.
ADMIN_LEVELS = {"bailiwick": 1, "provostship": 2, "sub_provostship": 2, "castellany": 2, "office": 2, "district": 2,
                "town_district": 2, "court": 3, "ban": 3, "mayoralty": 3, "val": 3}
SIMPLIFY_M = 80         # geometry simplification tolerance
PRECISION = 5           # decimal places in output coordinates (~1 m)
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
COMMUNE_CLASSES = {"Q484170", "Q262166", "Q116457956", "Q42744322", "Q15632617", "Q2919801"}

_to_metric = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform
_to_lonlat = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True).transform


def excluded_from_areas(geocoding_rows: list[dict], keep: set[str] = frozenset()) -> set[str]:
    """Places whose point must not add land: placed at their commune, matched with low
    confidence, or far from their district's other members without the index's commune or canton
    to confirm the match (a fief can lie far from the prévôté it is listed under: Harchéchamp,
    near Neufchâteau, in the prévôté of Nancy). `keep`: places a rules.yaml geocode rule gives land
    all the same (`land: true`), alone at a commune the book doesn't name (Fliessborn at Vry)."""
    return {g["place_id"] for g in geocoding_rows
            if g["place_id"] not in keep and (
                g["method"] in ("approximate", "unlocated")
                or g["confidence"] == "low"
                or ("km from its district" in g["note"] and "near the index's" not in g["note"]))}


def foreign_zones() -> list[tuple[float, float, float, str | None]]:
    """manual/foreign_lands.csv: the foreign lands inside or along the duchy (the Three Bishoprics'
    cities and countrysides, the bishops' towns, Nassau-Saarbrücken), as (x, y, radius) in metres
    around the commune each is named after, and the country its communes must be in today, if any:
    Nassau-Saarbrücken's circle stops at the border, Schœneck and Stiring were the county of Forbach's."""
    if not FOREIGN_LANDS.exists():
        return []
    by_name = {}
    for it in wikidata.region().values():
        if it["types"] & COMMUNE_CLASSES:
            for label in (it["de"], it["fr"]):   # French last: "Metz", "Sarrebruck" or "Saarbrücken"
                if label:
                    by_name[label] = it
    out = []
    for r in csv.DictReader(FOREIGN_LANDS.open()):
        it = by_name.get(r["centre"])
        if it is None:
            raise ValueError(f"manual/foreign_lands.csv: no commune {r['centre']!r}")
        x, y = _to_metric(it["lon"], it["lat"])
        out.append((x, y, float(r["radius_km"]) * 1000, (r.get("country") or "").strip() or None))
    return out


def neutral_points(listed: list[tuple[float, float]], qids: set[str], names: set[str],
                   zones: list[tuple] | None = None) -> list[tuple[float, float]]:
    """Communes the book doesn't list (metric coordinates) inside the foreign lands (`zones`):
    they keep their land out of the duchy's areas. Everywhere else, as in hist_map, only the
    book's places divide the land. A commune named like one of the book's places (unlocated ones
    included) or like a commune the index gives for a hamlet is not foreign land either. Without
    `zones`, every unlisted commune is neutral."""
    grid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    for x, y in listed:
        grid[(int(x // 2000), int(y // 2000))].append((x, y))

    def near_listed(x: float, y: float) -> bool:
        gx, gy = int(x // 2000), int(y // 2000)
        return any((x - a) ** 2 + (y - b) ** 2 < (NEUTRAL_MIN_KM * 1000) ** 2
                   for i in (-1, 0, 1) for j in (-1, 0, 1) for a, b in grid.get((gx + i, gy + j), []))

    out = []
    for it in wikidata.region().values():
        if it["qid"] in qids or not it["types"] & COMMUNE_CLASSES:
            continue
        if any(label_keys(it[lang]) & names for lang in ("fr", "de") if it[lang]):
            continue
        x, y = _to_metric(it["lon"], it["lat"])
        if zones is not None and not any((x - z[0]) ** 2 + (y - z[1]) ** 2 <= z[2] ** 2
                                         and (len(z) < 4 or z[3] is None or z[3] == it["country"]) for z in zones):
            continue
        if not near_listed(x, y):
            out.append((round(x), round(y)))
    return sorted(set(out))  # two items at one spot (a commune and its former commune) are one point


def cells_for(points: dict[tuple[float, float], list[str]], neutral: list[tuple[float, float]]):
    """Voronoi cells (metres) for listed points {(x, y): [place ids]} and neutral points;
    returns {(x, y): cell} for the listed points only."""
    keys = list(points)
    all_pts = [Point(k) for k in keys] + [Point(n) for n in neutral]
    region = unary_union([Point(k).buffer(CLIP_KM * 1000, 24) for k in keys])
    vor = shapely.voronoi_polygons(MultiPoint(all_pts), extend_to=region.envelope, ordered=True)
    return {k: cell.intersection(region) for k, cell in zip(keys, list(vor.geoms)[:len(keys)])}


def _feature(geom, props: dict) -> dict:
    geom = shapely.set_precision(transform(_to_lonlat, geom.simplify(SIMPLIFY_M)), 10 ** -PRECISION)
    return {"type": "Feature", "properties": props, "geometry": mapping(geom)}


def run() -> None:
    ds = store.load()
    places = {p.id: p for _, p in ds.places}
    with (config.CURATED_DIR / "geocoding.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    geocoding = {g["place_id"]: g for g in rows}
    rules = (load_rules().get("geocode") or {})
    no_land = excluded_from_areas(rows, {pid for pid, r in rules.items() if r.get("land")})
    located = [p for p in places.values() if p.kind == "settlement" and p.lat is not None]

    # One cell per point; places at the same point (a hamlet placed at its commune) share it,
    # and a place that adds land owns it.
    by_point: dict[tuple[float, float], list[str]] = defaultdict(list)
    for p in located:
        if p.id not in no_land:
            by_point[tuple(round(v) for v in _to_metric(p.lon, p.lat))].append(p.id)
    for pts in by_point.values():
        pts.sort(key=lambda pid: (CONFIDENCE_RANK.get(places[pid].geo_confidence or "high", 0), pid))
    qids = {p.wikidata_id for p in located if p.wikidata_id}
    names = {name_key(n) for p in places.values() if p.kind == "settlement"
             for n in [p.name_fr, p.index_commune or "", *p.variants] if n} - {""}
    neutral = neutral_points(list(by_point), qids, names, foreign_zones())
    print(f"cells: {len(by_point)} listed points, {len(neutral)} neutral communes")
    point_cells = cells_for(by_point, neutral)
    cells = {ids[0]: point_cells[pt] for pt, ids in by_point.items()}
    cell_of = {pid: ids[0] for ids in by_point.values() for pid in ids}

    # Every link counts, as in hist_map: a settlement listed under two prévôtés ("en partie", or
    # twice) is in both, and its cell in both areas. `shared` names the members that are also in
    # another territory of the same hierarchy (the app hatches them).
    children: dict[tuple[str, str], list[str]] = defaultdict(list)
    parents_of: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, m in ds.memberships:
        if m.relation not in ("admin", "feudal") or m.child_id not in places:
            continue
        children[(m.parent_id, m.relation)].append(m.child_id)
        if places[m.child_id].kind == "settlement":
            parents_of[(m.child_id, m.relation)].add(m.parent_id)

    def members(tid: str, relation: str) -> tuple[set[str], set[str]]:
        """(settlements whose cells form the area, those of them also in another territory)."""
        own, seen, queue = set(), {tid}, [tid]
        while queue:
            for c in children.get((queue.pop(), relation), ()):
                if places[c].kind == "settlement":
                    own.add(c)
                elif c not in seen:
                    seen.add(c)
                    queue.append(c)
        shared = {c for c in own if len(parents_of[(c, relation)]) > 1}
        return own, shared

    depth: dict[str, int] = {}

    def level(tid: str) -> int:
        """Administrative divisions by their kind (ADMIN_LEVELS: bailliages 1, prévôtés and offices 2,
        bans and mairies 3), never above their parent: the district of Bitche, under the duchy, is an
        office (2), and its mairies are mairies (3). Feudal realms by depth."""
        if tid not in depth:
            parent = next((m.parent_id for _, m in ds.memberships if m.child_id == tid
                           and m.relation in ("admin", "feudal")), None)
            below = level(parent) + 1 if parent else 1
            kind = ADMIN_LEVELS.get(places[tid].place_type) if places[tid].hierarchy == "admin" else None
            depth[tid] = 0 if tid == "duchy-lorraine" else max(below, kind or 0)
        return depth[tid]

    features, empty = [], []
    for t in sorted((p for p in places.values() if p.kind == "territory"), key=lambda t: t.id):
        relation = "admin" if t.hierarchy == "admin" else "feudal"
        own, shared = members(t.id, relation)
        area_ids = {cell_of[m] for m in own if m in cell_of and cell_of[m] in cells}
        if not area_ids:
            empty.append(t.id)
            continue
        geom = unary_union([cells[c] for c in area_ids])
        features.append(_feature(geom, {
            "id": t.id, "hierarchy": t.hierarchy, "place_type": t.place_type, "level": level(t.id),
            "settlements": len(own), "shared": sorted(shared)}))

    sharing = {ids[0]: ids[1:] for ids in by_point.values()}
    cell_features = [_feature(geom, {"id": pid, "also": sharing.get(pid, [])}) for pid, geom in sorted(cells.items())]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, feats in (("cells", cell_features), ("territories", features)):
        path = OUT_DIR / f"{name}.geojson"
        path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False,
                                   separators=(",", ":")))
        print(f"wrote {path.relative_to(config.ROOT)}: {len(feats)} features, {path.stat().st_size / 1e6:.1f} MB")
    print(f"territories with an area: {len(features)}/{len(features) + len(empty)}; without located members: "
          + ", ".join(empty))
    for name, ids in (("bailliages", lambda f: f["properties"]["level"] == 1 and f["properties"]["hierarchy"] == "admin"),
                      ("realms", lambda f: f["properties"]["hierarchy"] == "feudal")):
        preview([f for f in features if ids(f)], OUT_DIR.parent / "review" / f"areas-{name}.png", name)


def preview(features: list[dict], path, title: str) -> None:
    """PNG of the given areas over all cells (for checking by eye)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cells = json.loads((OUT_DIR / "cells.geojson").read_text())["features"]
    fig, ax = plt.subplots(figsize=(11, 11))
    for f in cells:
        g = shape(f["geometry"])
        for poly in getattr(g, "geoms", [g]):
            ax.plot(*poly.exterior.xy, color="#dddddd", linewidth=0.25)
    colors = plt.get_cmap("tab20")
    for i, f in enumerate(features):
        g = shape(f["geometry"])
        for poly in getattr(g, "geoms", [g]):
            ax.fill(*poly.exterior.xy, color=colors(i % 20), alpha=0.6, linewidth=0)
            for hole in poly.interiors:
                ax.fill(*hole.xy, color="white", linewidth=0)
        c = g.representative_point()
        ax.annotate(f["properties"]["id"], (c.x, c.y), fontsize=6, ha="center")
    for name, lon, lat in (("Metz", 6.1757, 49.1193), ("Toul", 5.8913, 48.6754), ("Verdun", 5.3845, 49.1598)):
        ax.plot(lon, lat, "k*", markersize=8)
        ax.annotate(name, (lon, lat), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_title(title)
    ax.set_aspect(1 / 0.66)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=80, bbox_inches="tight")
    plt.close(fig)
