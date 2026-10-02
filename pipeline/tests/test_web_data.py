import json

import pytest

from denombrement import config, web_data


def test_compact():
    assert web_data._compact({"a": 1, "b": None, "c": "", "d": [], "e": {}, "f": False, "g": 0}) == {"a": 1, "g": 0}


def test_attrs():
    assert web_data._attrs("gistes=2; provostship=Arches; also=Hobeneck|La plaine") == {
        "gistes": 2, "provostship": "Arches", "also": ["Hobeneck", "La plaine"]}
    assert web_data._attrs(None) == {}


@pytest.mark.skipif(not (config.WEB_DATA_DIR / "meta.json").exists(), reason="run make build-data first")
def test_built_data():
    meta = json.loads((config.WEB_DATA_DIR / "meta.json").read_text())
    assert meta["year"] == 1594 and meta["counts"]["entries"] >= 2480
    places = {p["id"]: p for p in json.loads((config.WEB_DATA_DIR / "places.json").read_text())}
    entries = json.loads((config.WEB_DATA_DIR / "entries.json").read_text())
    assert [e["no"] for e in entries[:3]] == [1, 2, 3]                    # the book's order
    assert all(e["place"] in places for e in entries)
    assert places["fief-keltern-ostern"]["counterpart"] == "provostship-keltern-ostern"
    for p in places.values():
        assert p["name"]["fr"] not in p.get("variants", [])
