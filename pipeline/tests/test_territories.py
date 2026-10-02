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
