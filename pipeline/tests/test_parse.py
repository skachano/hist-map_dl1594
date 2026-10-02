from pathlib import Path

from denombrement.parse import features, numbering, structure

LAST = 2487


def test_number_costs():
    assert numbering.cost("1546", 1546) == 0
    assert numbering.cost("1555", 1553) < 0.5          # 3 read as 5
    assert numbering.cost("4457", 1457) < 0.5          # 1 read as 4
    assert numbering.cost("5G", 56) < 0.5              # G for 6
    assert numbering.cost("2«>", 29) < 1.0             # 9 read as two symbols
    assert numbering.cost("Item", 30) > numbering.MAX_COST


def test_leading_token():
    assert numbering.leading_token("1546. Kelternostern.") == "1546"
    assert numbering.leading_token("221S< Ranschborn.") == "221S<"
    assert numbering.leading_token("Domaine.") is None
    assert numbering.leading_token("Ban Sainct-Diey.") is None


def test_assign_recovers_from_misreadings():
    # 1-2, then 3 read as "5" and "45-" for 4: greedy reading would drift; the alignment doesn't.
    tokens = ["1", "2", "5", "45-", "5", None, "G", "7"]
    readings = numbering.assign(tokens, LAST)
    assert [r.number if r else None for r in readings] == [1, 2, 3, 4, 5, None, 6, 7]


def test_assign_rejects_words():
    readings = numbering.assign(["1", "2", "P", "3"], LAST)
    assert [r.number if r else None for r in readings] == [1, 2, None, 3]


def test_find_in_a_line():
    text = "Sainct-Remvmonl.1156. Allainville."
    start, body, tok = numbering.find_in(text, 1156)
    assert tok == "1156" and text[body:] == "Allainville."
    assert numbering.find_in("Le Saulruz, de mesme. ïi. Arth-sur-Meurthe.", 5) is not None


def test_sections():
    assert structure._section_of("Domaine.") == "domain"
    assert structure._section_of("Doroaine.") == "domain"
    assert structure._section_of("Fiedvcz.") == "fief"
    assert structure._section_of("Nancy pour le clergé.") == "clergy"
    assert structure._section_of("Villages du chapitre de Toul qui sont des sauvegardes de") == "safeguard"
    assert structure._section_of("Prévosté et chastellainie de Charmes.") is None


def test_heading_types_and_seats():
    h = structure.classify("Prévosté et chastellainie de Rosières.")
    assert (h.types, h.level, h.seat) == (["provostship"], 2, "Rosières")
    h = structure.classify("L'office et chastcllainic de Seliawcmbourg.")
    assert (h.types, h.seat) == (["office"], "Seliawcmbourg")
    h = structure.classify("Prévostéet ehastellainiede Darney.")
    assert h.seat == "Darney"
    h = structure.classify("Le ban de Tcintruz, sçavoir")
    assert (h.types, h.level, h.seat) == (["ban"], 3, "Tcintruz")
    h = structure.classify("Terre de Commercy, souveraineté de Lorraine, contre les comtes de la Roche.")
    assert (h.types, h.seat) == (["lordship"], "Commercy")
    h = structure.classify("La terre et seigneurie de Faulquemont.")
    assert h.types == ["lordship"] and not h.pair
    assert structure.classify("Le comté de Challigny,") is None              # a list item
    assert structure.classify("Le comté de Challigny,", comma_ok=True) is not None
    assert structure.classify("Soubz ceste mairie est ladicte villette de Kaltenhaussen") is None  # a sentence


def test_overrides():
    h = structure.classify("Prévosté de Keuern-Qsternet autres villages de la chastelkùnie de Sehawembourg")
    assert h.pair and h.seat == "Keltern-Ostern" and h.types == ["provostship", "fief"]
    assert structure.classify("Raon.").types == ["district"]
    assert structure.classify("Raon,") is None
    assert structure.classify("Bassigny.").prose


def test_entry_details():
    text = "Lunéville, chasteau, ville, abbayede l'ordre régulier de sainct Augustin, commanderie."
    assert structure.entry_name(text) == "Lunéville"
    assert {"castle", "town", "abbey", "commandery"} <= set(structure.descriptors(text))
    assert structure.order_of(text) == "augustinian"
    assert structure.share_of("Einvau, partie.") == ("part", "partie")
    assert structure.share_of("Commercy, pour la moitié contre les sieurs comtes de la Roche.")[0] == "1/2"


def test_gazetteer_loose_keys(tmp_path: Path):
    (tmp_path / "old_forms.csv").write_text("page,old,modern,ok,text\n176,Einville,Euville,1,x\n")
    (tmp_path / "index.csv").write_text("page,name\n204,Einvillc\n205,Euville\n")
    g = structure.Gazetteer(tmp_path)
    assert g.modern_name("Einvilte") == "Einvillc"        # the index's place, not the old form's
    assert g.modern_name("Einville") == "Euville"         # an exact old form wins


def _lines(*texts, page="40"):
    return [(page, "denombrement", t) for t in texts]


def test_parse_a_passage():
    g = structure.Gazetteer(Path("/nonexistent"))
    lines = _lines(
        "Bailliage de Nancy.",
        "Soubz ce bailliage sont les prévostez et chastellainies de",
        "Rosières, Charmes et Forbach.",
        "Prévosté et chastellainie de Rosières.",
        "Domaine.",
        "1. Rosières, ville, chasteau et sallines.",
        "2. Einvau, partie.",
        "Le ban de Vagny.",
        "3. Vagney.",
        "Fiedvez.",
        "Terre de Pierrefort.",
        "4. Pierrefort, chasteau.",
        "La terre et seigneurie de Forbach.",
        "5. Forbach, chasteau et ville.",
    )
    r = structure.parse(lines, g)
    e = {x.no: x for x in r.entries}
    assert [x.no for x in r.entries] == [1, 2, 3, 4, 5]
    assert e[1].district == "provostship-rosieres" and e[1].section == "domain"
    assert e[2].share == "part"
    assert e[3].district == "ban-vagny"
    t = r.territories
    # A realm inside a district answers to the prévôté, and its entries keep the prévôté as district.
    assert e[4].realm == "lordship-pierrefort" and e[4].district == "provostship-rosieres"
    assert t["lordship-pierrefort"].ressort == "provostship-rosieres"
    # A terre the bailliage lists among its prévôtés is a slot: a division and a realm.
    assert e[5].district == "district-forbach" and e[5].realm == "lordship-forbach"
    assert t["district-forbach"].counterpart == "lordship-forbach" and t["district-forbach"].basis == "slot"
    assert t["district-forbach"].parent == "bailiwick-nancy"


def test_chaumes():
    rows = features.parse_chaumes([
        ("118", "Soub la prévosté d'Arches"),
        ("118", "Fonyer, en allemand Schinnbsberg, une giste."),
        ("118", "Ficherai, aliàs Fischern et Champy, deux gistes."),
    ])
    assert [r["name"] for r in rows] == ["Fonyer", "Ficherai"]
    assert rows[0]["attrs"] == "gistes=1; provostship=Arches; also=Schinnbsberg"
    assert "gistes=2" in rows[1]["attrs"] and "Champy" in rows[1]["attrs"]
