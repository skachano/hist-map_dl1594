from denombrement.text import clean, corrections, indexes, layout, pagemap
from denombrement.text.layout import Line


def test_dehyphenate_keeps_compound_names():
    assert clean.dehyphenate(["Ez prévosté et chas-", "tellainie de Kerling-", "lès-Sierck"]) == \
        "Ez prévosté et chastellainie de Kerling-lès-Sierck"


def test_fix_ocr_common_words():
    assert clean.fix_ocr("Frouarl, bourg el cbasleau, Saincl-Benoist") == "Frouarl, bourg et chasteau, Sainct-Benoist"
    assert clean.fix_ocr("Dudiet village, cl ladiete ville") == "Dudict village, et ladicte ville"
    assert clean.fix_ocr("Delle, Eltz") == "Delle, Eltz"  # only whole words


def test_fix_name_first_letter():
    assert clean.fix_name("llagécourt") == "Hagécourt"
    assert clean.fix_name("lmling") == "Imling"
    assert clean.fix_name("Illingen") == "Illingen"
    assert clean.fix_name(".Morhange") == "Morhange"


def test_page_labels():
    assert pagemap.printed(5) == "VI"
    assert pagemap.printed(47) == "36"
    assert pagemap.printed(277) == "c2"
    assert pagemap.printed(286) is None


def test_header_agreement_tolerates_3_5():
    assert pagemap.agrees("— 36 —", "36")
    assert pagemap.agrees("— 55 —", "35")       # 3 read as 5
    assert pagemap.agrees("—4iG—", "416") is True
    assert pagemap.agrees("— 07 —", "57") is False
    assert pagemap.agrees("", "57") is None


def test_note_start():
    assert layout.NOTE_START.match("1. Celte carte se trouve")
    assert layout.NOTE_START.match("i. Voy., au sujet")
    assert layout.NOTE_START.match("*. A l'époque")
    assert not layout.NOTE_START.match("Monseigneur,")


def test_expand_numbers():
    assert indexes.expand_numbers(["1475", "1537", "38"]) == [1475, 1537, 1538]
    assert indexes.expand_numbers(["2240", "67", "2355", "2402"]) == [2240, 2267, 2355, 2402]
    assert indexes.expand_numbers(["709-715"]) == list(range(709, 716))
    assert indexes.expand_numbers(["1098", "13"]) == [1098, 1113]


def test_parse_index_entry():
    e = indexes.parse_entry("189", "Beckingen, vil. (commanderie), com. de Haustadt, canton de Merzig, 1450, 2485.")
    assert (e.name, e.kind, e.commune, e.canton) == ("Beckingen", "vil. (commanderie)", "Haustadt", "Merzig")
    assert e.numbers == [1450, 2485] and e.numbers_ok and e.identified

    e = indexes.parse_entry("183", "Agémont1, ham., coin, de Dommartin-aux-Bois, 1029.")
    assert (e.name, e.marker, e.commune, e.numbers) == ("Agémont", "1", "Dommartin-aux-Bois", [1029])

    e = indexes.parse_entry("260", "Weiskirch. canlon de Volmunster, 2101.")
    assert (e.name, e.canton, e.numbers) == ("Weiskirch", "Volmunster", [2101])

    e = indexes.parse_entry("185", "Affieville, canton de Conflans (Moselle), 1950.")
    assert (e.canton, e.region) == ("Conflans", "Moselle")

    e = indexes.parse_entry("244", "Ruchlingen, vil. détruit, prés de Spickeren, 1728.")
    assert e.near == "Spickeren" and e.identified

    e = indexes.parse_entry("188", "Ban Saint-Pierre. Voy. Aoury.")
    assert e.xref == "Aoury" and e.numbers_ok and not e.numbers

    e = indexes.parse_entry("207", "Fliessborn5, prévôté de Sierck, 1504.")
    assert not e.identified  # located only by a historical unit


def test_index_numbers_flagged_and_reread():
    e = indexes.parse_entry("210", "Frouard, canton de Nancy-Nord, 8, 2507.")
    assert not e.numbers_ok  # beyond the last entry
    e = indexes.parse_entry("201", "Dalstein, canton de Bouzonville, 126».")
    assert not e.numbers_ok
    assert indexes.merge_reading(e, "Dalstein, canton de Bouzonville, 1265.")
    assert e.numbers == [1265] and e.numbers_source == "tesseract"
    e = indexes.parse_entry("231", "Aydoiles, canton de Bruyères, 590, 6a1.")
    assert not indexes.merge_reading(e, "Aydoiles, canton de Bruyères, 590, 741.")  # disagrees on a read digit
    assert indexes.merge_reading(e, "Aydoiles, canton de Bruyères, 590, 641.") and e.numbers == [590, 641]


def test_old_forms():
    f = indexes.split_old_form("Abbertingen. Olberding.")
    assert (f.old, f.modern, f.ok) == ("Abbertingen", "Olberding", True)
    f = indexes.split_old_form("Exweiller%Thaleckswcilcr.")
    assert (f.old, f.modern) == ("Exweiller", "Thaleckswcilcr")
    assert not indexes.split_old_form("Mous. Mont-devant-Sassey. Montagne (la). Saint-Privat.").ok


def _corr(text: str) -> corrections.Correction:
    c = corrections.Correction(1, "c1", "224", "index", lines=[text])
    corrections._classify(c)
    return c


def test_corrections_classified():
    c = _corr("P. 224, art. Lcngelsheim, lisez 2144, au lieu de 2145.")
    assert (c.action, c.article, c.old, c.new, c.auto) == ("renumber", "Lcngelsheim", "2145", "2144", True)
    c = _corr("P. 212, 5e ligne, au lieu de Bcltnach, lisez : Bettnach.")
    assert (c.action, c.old, c.new) == ("replace", "Bcltnach", "Bettnach")
    c = _corr("Effacez Rolling (c'est Rouhling, ci-après).")
    assert (c.action, c.article, c.auto) == ("delete", "Rolling", True)
    c = _corr("Titling, mis à la p. 252, doit venir à la p. suivante, après Tilleux.")
    assert (c.action, c.article, c.new) == ("move", "Titling", "après Tilleux")
