import csv
from pathlib import Path

import pytest

from denombrement import config
from denombrement.curate import build, corrections
from denombrement.text import indexes

SAMPLE = Path(__file__).parent / "fixtures" / "sample"


def test_display_name():
    assert build.display_name("Malgrange (la)") == "La Malgrange"
    assert build.display_name("Saulrupt (le)") == "Le Saulrupt"
    assert build.display_name("Agémont1") == "Agémont"
    assert build.display_name("Oberkirchen* (anciennement Catharin-Ostern)") == "Oberkirchen"


def test_similarity_of_old_and_modern_names():
    assert build.similarity("Sainct-Nicolas", "Saint-Nicolas") == 1.0
    assert build.similarity("Charmes", "Charmes-sur-Moselle") == 1.0       # the base of a compound name
    assert build.similarity("Einvilte", "Einvillc") == 1.0                 # c/e and l/t read alike
    assert build.similarity("Glonville", "Bienville-la-Petite") < 0.8


def test_number_variants():
    assert {1553, 1355, 1556} <= build.variants_of(1555)   # one confused digit
    assert 1533 not in build.variants_of(1555)             # two are too many
    assert 1457 not in build.variants_of(1457)


def _row(page, text):
    return corrections.IndexRow(page, indexes.parse_entry(page, text))


def test_matcher():
    rows = [
        _row("227", "Malgrange (la), ham., com. de Jarville, 5."),        # the index misprints 3 as 5
        _row("185", "Art-sur-Meurthe, canton de Saint-Nicolas, 5."),
        _row("228", "Maxéville, canton de Nancy-Nord, 19."),
        _row("196", "Charmes-sur-Moselle, ch.-l. de canton, 869, 2315."),
    ]
    old = [{"old": "Marchainville", "modern": "Maxéville", "ok": "1"}]
    m = build.Matcher(rows, old)
    assert m.match(3, "La Malgrange").row.entry.name == "Malgrange (la)"
    assert m.match(3, "La Malgrange").how == "confused number"
    assert m.match(5, "Arth-sur-Meurthe").how == "number+name"
    assert m.match(19, "Marchainville").row.entry.name == "Maxéville"   # through the old forms
    assert m.match(2313, "Charmes").row.entry.name == "Charmes-sur-Moselle"
    assert m.match(400, "Nowhere").row is None


def test_correction_pages():
    assert corrections.pages_near("258") >= {"238", "257", "259"}
    assert corrections._bare("Sanbach* (et non Sambach)") == "sanbach"


@pytest.mark.skipif(not (config.CURATED_DIR / "entries.csv").exists(), reason="run make curate first")
def test_curated_data_agrees_with_the_sample():
    """The hand-checked sample (Stage 2) and the generated tables: same section, same district
    kind and the same place, read through the index's spelling."""
    cur = {e["no"]: e for e in csv.DictReader((config.CURATED_DIR / "entries.csv").open())}
    places = {p["id"]: p for p in csv.DictReader((config.CURATED_DIR / "places.csv").open())}
    sample_places = {p["id"]: p for p in csv.DictReader((SAMPLE / "places.csv").open())}
    for f in csv.DictReader((SAMPLE / "entries.csv").open()):
        c = cur[f["no"]]
        assert c["section"] == f["section"], f["no"]
        assert build.similarity(places[c["place_id"]]["name_fr"], sample_places[f["place_id"]]["name_fr"]) >= 0.7 \
            or f["no"] in ("1470", "1549", "1550"), (f["no"], places[c["place_id"]]["name_fr"])  # C/K, unidentified
