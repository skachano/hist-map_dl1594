from denombrement.geo import geocode
from denombrement.geo.geocode import Cand, Gazetteer


def test_keys():
    assert geocode.name_key("Robrbacb") == geocode.name_key("Rohrbach")   # b/h, c/e
    assert geocode.label_keys("Sierck-les-Bains") >= {geocode.name_key("Sierck")}
    assert geocode.clean_place_name("île Gorze") == "Gorze"
    assert geocode.clean_place_name("Lunévillc-Nord") == "Lunévillc"
    assert geocode.clean_place_name("Fresnes-en-Voèvre(Meuse;, 1891") == "Fresnes-en-Voèvre"


def test_place_names():
    names = geocode.place_names({"name_fr": "Mondorff", "variants": "Mondorff, aliàs Mamendorff|Wach-Haussen ou Schweich"})
    assert {"Mondorff", "Mamendorff", "Wach-Haussen", "Schweich"} <= names


def _gaz(*cands):
    g = Gazetteer({}, [], [])
    for c in cands:
        g.cands.append(c)
        for k in c.keys:
            g.by_key[k].append(c)
        g.grid[(int(c.lat * 10), int(c.lon * 10))].append(c)
    return g


def test_best_near_prefers_the_namesake_near_the_anchor():
    near = Cand("wikidata", 48.70, 6.20, geocode.label_keys("Viller"), 3, "FR", qid="Q1", raw=geocode.raw_keys(["Viller"]))
    far = Cand("wikidata", 49.40, 6.70, geocode.label_keys("Viller"), 3, "FR", qid="Q2", raw=geocode.raw_keys(["Viller"]))
    g = _gaz(near, far)
    hit = g.best_near(geocode.raw_keys(["Viller"]), (48.69, 6.18), 25)
    assert hit and hit[0].qid == "Q1"
    assert g.best_near(geocode.raw_keys(["Viller"]), (47.0, 5.0), 25) is None
    assert g.best_near(geocode.raw_keys(["Viller"]), (48.69, 6.18), 25, exclude=frozenset({"Q1"})) is None


def test_best_near_tolerates_ocr():
    c = Cand("wikidata", 48.9, 6.0, geocode.label_keys("Maidières"), 3, "FR", qid="Q3", raw=geocode.raw_keys(["Maidières"]))
    hit = _gaz(c).best_near(geocode.raw_keys(["Maidiures"]), (48.9, 6.03), 25)
    assert hit and hit[0].qid == "Q3" and hit[1] >= 0.84


def test_km():
    assert 108 < geocode.km((48.0, 6.0), (49.0, 6.0)) < 114


def test_village_names_keep_b_and_h_apart():
    c = Cand("wikidata", 48.6, 6.6, geocode.label_keys("Bénaménil"), 3, "FR", qid="Q4", raw=geocode.raw_keys(["Bénaménil"]))
    assert Gazetteer.sim(geocode.raw_keys(["Hénaménil"]), c) < 1.0
