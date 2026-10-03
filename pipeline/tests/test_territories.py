import csv

from shapely.geometry import Point

from denombrement.geo import territories as t


def test_excluded_from_areas():
    rows = [
        {"place_id": "a", "method": "wikidata", "confidence": "high", "note": ""},
        {"place_id": "b", "method": "approximate", "confidence": "low", "note": "placed at its commune"},
        {"place_id": "c", "method": "wikidata", "confidence": "medium", "note": "1.00 near the index's canton; 40 km from its district"},
        {"place_id": "d", "method": "geonames", "confidence": "low", "note": "ambiguous"},
    ]
    assert t.excluded_from_areas(rows) == {"b", "c", "d"}


def test_a_neutral_seed_makes_a_hole():
    # Three listed villages around a foreign commune in the middle: its land is nobody's.
    listed = {(0.0, 0.0): ["a"], (4000.0, 0.0): ["b"], (2000.0, 3000.0): ["c"]}
    centre = (2000.0, 1000.0)
    cells = t.cells_for(listed, [centre])
    assert not any(cell.contains(Point(centre)) for cell in cells.values())
    without = t.cells_for(listed, [])
    assert any(cell.contains(Point(centre)) for cell in without.values())


def test_cells_are_clipped():
    cells = t.cells_for({(0.0, 0.0): ["a"], (50000.0, 0.0): ["b"]}, [])
    assert not cells[(0.0, 0.0)].contains(Point(25000, 0))   # beyond CLIP_KM of both: no one's land


def test_a_settlement_in_two_divisions_is_in_both_areas():
    """As in hist_map: every membership counts; Athienville is in the prévôtés of Einville and Lunéville."""
    import json
    from shapely.geometry import Point, shape
    from denombrement import config
    areas = {f["properties"]["id"]: f for f in json.loads((config.DATA_DIR / "geometry" / "territories.geojson")
                                                          .read_text())["features"]}
    places = {p["id"]: p for p in csv.DictReader((config.CURATED_DIR / "places.csv").open())}
    point = Point(float(places["athienville"]["lon"]), float(places["athienville"]["lat"]))
    for tid in ("provostship-einville", "provostship-luneville"):
        assert shape(areas[tid]["geometry"]).buffer(0.001).contains(point), tid
        assert "athienville" in areas[tid]["properties"]["shared"], tid


def test_shared_lands_of_a_division_and_its_realm():
    from denombrement.curate import build
    out = build.Built()
    out.places = {
        "office-x": {"id": "office-x", "kind": "territory", "hierarchy": "admin", "counterpart_id": "lordship-x",
                     "counterpart_basis": "slot", "name_fr": "Office de X"},
        "lordship-x": {"id": "lordship-x", "kind": "territory", "hierarchy": "feudal", "name_fr": "Seigneurie de X"},
        "abbey-y": {"id": "abbey-y", "kind": "territory", "hierarchy": "feudal", "name_fr": "Temporel de Y"},
        **{v: {"id": v, "kind": "settlement"} for v in ("a", "b", "c")},
    }
    out.memberships = [
        {"child_id": "a", "parent_id": "office-x", "relation": "admin"},   # the office's: also the lordship's
        {"child_id": "b", "parent_id": "lordship-x", "relation": "feudal"},  # the lordship's: also the office's
        {"child_id": "c", "parent_id": "office-x", "relation": "admin"},   # in another realm: stays out
        {"child_id": "c", "parent_id": "abbey-y", "relation": "feudal"},
    ]
    build._shared_lands(out)
    got = {(m["child_id"], m["parent_id"]) for m in out.memberships}
    assert ("a", "lordship-x") in got and ("b", "office-x") in got and ("c", "lordship-x") not in got
