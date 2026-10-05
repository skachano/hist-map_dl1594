from denombrement.geo import dicotopo
from denombrement.geo.dicotopo import Hit, Index


def _place(pid, label, old=(), lat=48.6, lon=6.3, description="", commune=None):
    return {"id": pid, "label": label, "old": list(old), "insee": "", "commune": commune or label, "dpt": "54",
            "canton": "", "lat": lat, "lon": lon, "description": description}


def test_spelling_key_brings_old_and_modern_spellings_together():
    k = dicotopo.spelling_key
    assert k("Flainvaulx") == k("Flainval") == "flainval"
    assert k("Fleinvalz") == "fleinval"
    assert k("Sainct Diey") == k("Saint-Diei")
    assert k("La Malgrange") == k("Malgrange (la)") == "malgrange"
    assert k("Foucquerey") == "foucuerei"


def test_old_labels():
    p = _place("P1", "Abaucourt", old=[
        "<dfn>Aubocurt</dfn> et <dfn>Aubocourt</dfn> (1178)",
        "<dfn>Hennezel et Reuxeulles, hameau, communauté de Tendon</dfn> (1711)",
        '<dfn>Henzelle</dfn> (<span class="sc">xix</span><sup>e</sup> siècle)',
        "De la part de Guillaume Hannezel, nostre controleur (1491)"])
    assert dicotopo.old_labels(p) == [("Aubocurt", "1178"), ("Aubocourt", "1178"), ("Hennezel", "1711"),
                                      ("Reuxeulles", "1711"), ("Henzelle", "")]


def test_kind():
    assert dicotopo.kind(_place("P1", "x", description='Hameau, commune de <a href="/places/P2">Tendon</a>.')) == "Hameau"
    assert dicotopo.kind(_place("P1", "x", description='Canton de <a href="/places/P3">Nomeny</a>.')) == ""
    assert dicotopo.kind(_place("P1", "x", description="Lieu dit, commune de Serres.")).startswith(dicotopo._LAND)


def test_ocr_confusions_are_cheap():
    k, sim = dicotopo.spelling_key, dicotopo.similarity
    assert dicotopo.ocr_distance("hainval", "flainval") == dicotopo._CHEAP        # fl read as H
    assert sim(k("Cleuveey"), k("Cleuvecy")) > 0.85     # "ee" is made single before the c/e can count
    assert sim(k("Gloi»ville"), k("Glonville")) > 0.85
    assert sim(k("Brecoocel"), k("Breconcel")) > 0.85   # likewise "oo"
    assert sim(k("Nancy"), k("Remiremont")) == 0.0                                # too different in length
    assert sim(k("Glonville"), k("Glonville")) == 1.0


def test_coarse_lets_multi_letter_confusions_through_the_sift():
    assert dicotopo.coarse("hainvau")[:3] == dicotopo.coarse("flainval")[:3]


def test_query_keys_drop_the_wording_around_a_name():
    keys = dict(dicotopo.query_keys("La ville dudict Sainct Dicy"))
    assert keys[dicotopo.spelling_key("Sainct Dicy")] == 1.0
    assert keys[dicotopo.spelling_key("Dicy")] == 0.85
    assert [k for k, _ in dicotopo.query_keys("La ville de Raon")] == ["raon"]


def test_search_finds_an_old_spelling_and_prefers_the_namesake_near_the_district():
    idx = Index([
        _place("P1", "Raon-l'Étape", old=["<dfn>Raon</dfn> (1458)"], lat=48.40, lon=6.84),
        _place("P2", "Raon-aux-Bois", old=["<dfn>Raon</dfn> (1428)"], lat=48.06, lon=6.52),
        _place("P3", "Braconseil", old=["<dfn>Breconcel</dfn> (1594)"], description="Hameau, commune de Clefcy."),
    ])
    hits = idx.search("La ville de Raon", near=(48.30, 6.95))
    assert [h.place["id"] for h in hits[:2]] == ["P1", "P2"]
    assert hits[0].spelling == "Raon" and hits[0].year == "1458" and round(hits[0].km) == 14
    hit = idx.search("Brecoocel")[0]
    assert hit.place["id"] == "P3" and hit.year == "1594"


def test_fields_and_streams_count_less_than_settlements():
    idx = Index([_place("P1", "Ormes (Fontaine d')", description="Fontaine, commune de Dombasle."),
                 _place("P2", "Ormes-et-Ville", old=["<dfn>Ormes</dfn> (1403)"])])
    assert idx.search("Ormes")[0].place["id"] == "P2"


def test_search_all_keeps_the_queries_order():
    idx = Index([_place("P1", "Glonville"), _place("P2", "Clefcy", old=["<dfn>Cleuvecy</dfn> (1580)"])])
    results = dicotopo.search_all(idx, [("Cleuveey", None, 1), ("Gloi»ville", None, 1), ("Zzzz", None, 1)])
    assert [[h.place["id"] for h in r] for r in results] == [["P2"], ["P1"], []]


def test_manual_checks(tmp_path, monkeypatch):
    f = tmp_path / "manual-check.md"
    f.write_text("### Entries not found in the index\n\n"
                 "- 38 Hainvau (p. 37, provostship-nancy)\n  + Flainval (written Flainvau) \n"
                 "- 70 Ormes (p. 38, provostship-nancy)\n", encoding="utf-8")
    monkeypatch.setattr(dicotopo, "MANUAL_CHECK", f)
    assert dicotopo.manual_checks() == [("38", "Hainvau", "provostship-nancy", "Flainval (written Flainvau)"),
                                        ("70", "Ormes", "provostship-nancy", "")]
    monkeypatch.setattr(dicotopo, "MANUAL_CHECK", tmp_path / "missing.md")
    assert dicotopo.manual_checks() == []


def test_answer_rank():
    hits = [Hit(_place("P1", "Einvaux"), "Ainvau", "1499", 0.8, None),
            Hit(_place("P2", "Flainval"), "Flainval", "", 0.79, None)]
    assert dicotopo._answer_rank(hits, "Flainval (written Flainvau)") == 2
    assert dicotopo._answer_rank(hits, "Anould") is None


def test_display_label():
    assert dicotopo.display_label("Faing-Thierry (Le)") == "Le Faing-Thierry"
    assert dicotopo.display_label("Orme (L’)") == "L’Orme"
    assert dicotopo.display_label("Aboncourt ou Aboncourt-sur-Seille") == "Aboncourt"
    assert dicotopo.display_label("Petit-Eberswiller") == "Petit-Eberswiller"


def test_shared_points_tell_a_hamlets_own_point_from_its_communes():
    places = [_place("P1", "Macheren", lat=49.09, lon=6.76),
              _place("P2", "Petit-Eberswiller", lat=49.09, lon=6.76, commune="Macheren"),
              _place("P3", "Mortagne", lat=48.546, lon=6.443, commune="Mont-sur-Meurthe")]
    # Petit-Eberswiller has its commune's point; Mortagne's is its own
    assert dicotopo.shared_points(places) == {(49.09, 6.76)}
