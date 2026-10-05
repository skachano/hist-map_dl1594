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


def test_a_rule_places_a_hamlet_at_its_commune():
    """rules.yaml geocode {at: commune}: an approximate point at that commune, the match dropped."""
    from denombrement.geo import geocode
    res = {"hutte": geocode.Result("hutte", lat=48.9, lon=7.2, wikidata_id="Q1", method="geonames", confidence="low")}
    rules = {"hutte": {"at": "Xamontarupt", "note": "a hamlet of Xamontarupt (the index)"}}
    geocode._apply_rules(res, rules, {}, lambda name, pid: (48.1, 6.6) if name == "Xamontarupt" else None)
    r = res["hutte"]
    assert (r.lat, r.lon, r.method, r.confidence, r.wikidata_id) == (48.1, 6.6, "approximate", "low", None)
    assert r.fixed and r.note == "a hamlet of Xamontarupt (the index)"


def test_a_rule_that_only_names_a_place_leaves_it_to_the_passes():
    """rules.yaml geocode {name_fr, note}: the name and the note, applied twice without repeating it;
    the place is not fixed, so the district and index passes can still move it."""
    from denombrement.geo import geocode
    res = {"mortagnc": geocode.Result("mortagnc", lat=48.5, lon=6.4, method="approximate", confidence="low",
                                      note="placed at its commune Mont")}
    rules = {"mortagnc": {"name_fr": "Mortagne", "note": "Mortagne, a hamlet of Mont-sur-Meurthe (DicoTopo)"}}
    geocode._apply_rules(res, rules, {})
    geocode._apply_rules(res, rules, {})
    r = res["mortagnc"]
    assert (r.name_fr, r.lat, r.lon, r.fixed) == ("Mortagne", 48.5, 6.4, False)
    assert r.note == "placed at its commune Mont; Mortagne, a hamlet of Mont-sur-Meurthe (DicoTopo)"
    assert not geocode.places_it(rules["mortagnc"]) and geocode.places_it({"at": "Mont"})


def test_a_rule_sets_a_point_names_and_country():
    """rules.yaml geocode {lat, lon, name_*, country}: a place the gazetteers give no item for (Köllig)."""
    from denombrement.geo import geocode
    res = {"kolchen": geocode.Result("kolchen", lat=49.6, lon=6.4, method="hist_map", confidence="low", country="FR")}
    rules = {"kolchen": {"lat": 49.63419, "lon": 6.44363, "name_fr": "Köllig", "name_de": "Köllig", "country": "DE",
                         "note": "Köllig, a village of Nittel"}}
    geocode._apply_rules(res, rules, {})
    r = res["kolchen"]
    assert (r.lat, r.lon, r.name_fr, r.name_de, r.country) == (49.63419, 6.44363, "Köllig", "Köllig", "DE")
    assert (r.method, r.confidence, r.fixed) == ("rule", "high", True)


def test_a_place_takes_the_country_of_the_nearest_item():
    """hist_map's points carry no country: the nearest Wikidata or GeoNames item's is taken
    (Kaisen, in the Saarland); a match's own country and a rule's stand."""
    from denombrement.geo import geocode
    illingen = Cand("wikidata", 49.376, 7.052, geocode.label_keys("Illingen"), 3, "DE", qid="Q1")
    g = _gaz(illingen)
    res = {"kaisen": geocode.Result("kaisen", lat=49.371, lon=7.017, method="hist_map", country="FR"),
           "metz": geocode.Result("metz", lat=49.37, lon=7.02, method="wikidata", country="FR"),
           "ruled": geocode.Result("ruled", lat=49.37, lon=7.02, method="rule", country="FR"),
           "far": geocode.Result("far", lat=48.0, lon=6.0, method="approximate", country="FR")}
    geocode._country_by_point(res, g, {"ruled": {"lat": 49.37, "lon": 7.02, "country": "FR"}})
    assert [res[k].country for k in ("kaisen", "metz", "ruled", "far")] == ["DE", "FR", "FR", "FR"]
