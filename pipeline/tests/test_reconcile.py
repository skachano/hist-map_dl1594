"""The index and the lists, number by number (curate/reconcile.py), and the index's communes."""
from denombrement.curate import build, corrections, reconcile
from denombrement.text import indexes


def _row(page: str, text: str) -> corrections.IndexRow:
    return corrections.IndexRow(page, indexes.parse_entry(page, text))


def _entry(no: int, name: str, text: str | None = None) -> dict:
    return {"no": no, "name": name, "text": text or f"{name}.", "series": "main", "page": "1"}


def _resolve(rows, entries, monkeypatch, manual=None):
    monkeypatch.setattr(reconcile, "load_manual", lambda: manual or {})
    m = build.Matcher(rows, [])
    matches = {e["no"]: m.match(e["no"], e["name"]) for e in entries}
    return reconcile.resolve(m.rows, entries, matches, m.sim, build.similarity)


def test_neighbours():
    assert 38 in reconcile.neighbours(58) and 1358 in reconcile.neighbours(358) and 35 in reconcile.neighbours(358)
    assert 58 not in reconcile.neighbours(58)


def test_numbers_resolved_both_ways(monkeypatch):
    rows = [_row("227", "Malgrange (la), ham., com. de Jarville, 5."),      # printed 3, read 5
            _row("185", "Art-sur-Meurthe, canton de Saint-Nicolas, 5."),
            _row("261", "Woelfling, canton de Sarreguemines, 2230."),       # one entry, two places
            _row("260", "Wieswiller, canton de Sarreguemines, 2230.")]
    entries = [_entry(3, "La Malgrange"), _entry(5, "Arth-sur-Meurlhe"), _entry(7, "Dombasle"),
               _entry(2230, "Volfflingen et Weissweiller")]
    res = _resolve(rows, entries, monkeypatch)
    got = {(x.row.entry.name, x.entry): x.status for x in res.links}
    assert got[("Malgrange (la)", 3)] == "corrected"
    assert got[("Art-sur-Meurthe", 5)] == "agrees"
    assert {("Woelfling", 2230), ("Wieswiller", 2230)} <= set(got)
    assert res.unnamed == [7]


def test_abbreviated_numbers_count_from_the_entry_meant(monkeypatch):
    # "1357, 95" read as "1557, 95": 95 is 1395, not 1595
    rows = [_row("259", "Volmerange, canton de Boulay, 1557, 95."),
            _row("246", "Saarwellingen, canton de Saarlouis, 1557."), _row("229", "Mellecey, canton de Givry, 1595.")]
    entries = [_entry(1357, "Wolmeringen"), _entry(1395, "Welmeringen"), _entry(1557, "Saarwellingen"),
               _entry(1595, "Mellecey")]
    res = _resolve(rows, entries, monkeypatch)
    assert sorted(x.entry for x in res.links if x.row is rows[0]) == [1357, 1395]


def test_a_decision_by_hand_wins(monkeypatch):
    rows = [_row("207", "Flainval, canton de Lunéville-Nord, 58.")]          # printed 38
    entries = [_entry(38, "Hainvau"), _entry(58, "Herbelmont")]
    key = ("207", reconcile._key("Flainval"), "58")
    res = _resolve(rows, entries, monkeypatch, {key: {"entry": "38", "note": "printed 38"}})
    assert [(x.entry, x.status) for x in res.links] == [(38, "manual")]


def test_index_communes_and_cantons():
    assert build._seat_key("Yal-d'Ajol") == "Val-d'Ajol"
    assert build._seat_key("Gelvécourl") == "Gelvécourt"
    assert build._seat_key("Perl") == "Perl"
    assert build._seat_key("Raon-1'Etape") == "Raon-l'Etape"
    assert build._garbled("Bouzonviiie") and build._garbled("llinckange")
    assert not build._garbled("Saint-Michel") and not build._garbled("Thionville")


def test_an_index_line_read_again_on_the_printed_page():
    """rules.yaml index_lines: the scan ran Bliesguerschwiller's line into the next one."""
    rows = [r for r in corrections.load_index() if r.page == "191" and r.entry.name.startswith("Bliesguersch")]
    assert len(rows) == 1
    assert rows[0].entry.canton == "Sarreguemines" and rows[0].entry.numbers == [1580]
    assert not rows[0].entry.commune     # not the next line's "com. de Bischmisheim"


def test_merged_index_lines_are_split():
    """Two printed lines the scan ran together become two index lines, each with its number."""
    rows = {r.entry.name: r.entry.numbers for r in corrections.load_index() if r.page in ("218", "256")}
    assert rows.get("Hœlling") == [2166] and rows.get("Hoéville") == [483]
    assert rows.get("Velle") == [1763] and rows.get("Velle-sur-Moselle") == [202]
    assert build.slug("Hœlling") == "hoelling"


def test_a_remark_after_the_numbers_is_not_part_of_them():
    e = indexes.parse_entry("254", "Nieder-Saubach, vil., com. de Lebach, canton de Saarlouis (Pr.), 1491. "
                                   "(C'est Sambach, ou plutôt Saubach, de la p. 245.)")
    assert e.numbers == [1491] and e.commune == "Lebach"
