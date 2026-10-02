"""Facts about this scan of the 1870 edition that are not worth detecting automatically."""

# Printed page numbering, by PDF page range (inclusive): printed = pdf - offset.
# The editor's introduction is numbered in roman numerals (V-XIV), the corrections
# restart at 1. Printed pp. 1-2 are probably Alix's title page and its blank verso,
# which the scan puts before the introduction (PDF 2-3).
ROMAN_PAGES = (4, 13)        # printed = pdf + 1, in roman numerals
ARABIC_PAGES = (14, 275)     # printed = pdf - 11
ARABIC_OFFSET = 11
CORRECTION_PAGES = (276, 283)  # printed = pdf - 275 (own numbering)
CORRECTION_OFFSET = 275
LAST_PDF = 283               # 284-288: series title, printer and colophon

# Parts of the book, in order: (id, first PDF page, regex of the part's first line on
# that page, or None when the part starts at the top of the page). A part runs until
# the next one starts.
PARTS: list[tuple[str, int, str | None]] = [
    ("title", 2, None),
    ("introduction", 4, None),            # the editor's introduction (V-XIV)
    ("alix-contents", 14, None),          # "Table du contenu au présent livre"
    ("epilogue", 18, None),               # dedication to the duke
    ("antiquity", 22, r"antiquit. du duch. de Lorraine"),
    ("singularities", 42, r"^DESCRIPTION SOMMAIRE DES SINGULARIT"),
    ("composition", 45, r"quelles provinces et bailliages"),
    ("denombrement", 45, r"^Bailliage de Nancy"),
    ("mines", 127, r"^Les mynes d'argent, plomb"),
    ("chaumes", 128, r"haultes ch.ulm"),
    ("rivers", 130, r"fleuves et rivi.res"),
    ("lists", 138, r"^Noms des villes e. bourg"),
    ("elogium", 145, r"^Elogium"),
    ("bitche", 147, r"pi.[lt]re d.di.a.oire"),
    ("editor-notes", 182, None),           # how the two tables were made
    ("old-forms", 186, None),              # Table des formes anciennes (two columns)
    ("index", 194, None),                  # Table des noms de lieux
    ("contents", 274, None),               # Table des matières of the volume
    ("corrections", 276, None),            # Corrections et rectifications
]

# The editor's numbering runs from 1 (Nancy) to 2487 (the Charterhouse of Rettel, last of
# the thematic lists).
LAST_ENTRY = 2487

# Pages set in two columns, read left column first.
TWO_COLUMN_PAGES = range(186, 194)

# Printed pages of the editor's tables, as the corrections cite them.
OLD_FORMS_PRINTED = (175, 182)
INDEX_PRINTED = (183, 262)
