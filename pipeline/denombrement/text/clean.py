"""Pure text-cleanup helpers for the OCR layer (no PDF access, easy to test)."""
from __future__ import annotations

import re

# Words that follow a hyphen in compound place names ("Kerling-lès-Sierck",
# "Hombourg-sur-Canner"); a line break after such a hyphen keeps the hyphen.
_COMPOUND_PARTICLES = {
    "lès", "les", "lez", "sur", "sous", "en", "le", "la", "aux", "au", "devant",
    "de", "du", "des", "et", "am", "an", "bei", "im", "auf", "der", "von",
}


def dehyphenate(lines: list[str]) -> str:
    """Join the lines of one paragraph, undoing end-of-line hyphenation."""
    text = ""
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if not text:
            text = line
        elif text.endswith("-") and not text.endswith(" -"):
            first_word = re.match(r"\w*", line).group()
            if first_word[:1].islower() and first_word not in _COMPOUND_PARTICLES:
                text = text[:-1] + line  # "Féné-" + "trange" -> "Fénétrange"
            else:
                text = text + line  # "Saint-" + "Avold", "Kerling-" + "lès-Sierck"
        else:
            text = text + " " + line
    return normalize_spaces(text)


def normalize_spaces(text: str) -> str:
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ([,.)])", r"\1", text)  # keep French spacing before ; and :
    text = re.sub(r"\( ", "(", text)
    return text.strip()


# The OCR's usual misreadings of common words in this font (c/e for t, l for t, b for h).
# Only words whose reading is certain; names are left to the index (Stage 3).
_WORD_FIXES = {
    "el": "et", "cl": "et",
    "ehasteau": "chasteau", "ebasteau": "chasteau", "cbasteau": "chasteau", "cbasleau": "chasteau",
    "ebasleau": "chasteau", "ehasleau": "chasteau", "chasleau": "chasteau", "chastcau": "chasteau",
    "cbasleaux": "chasteaux", "chasleaux": "chasteaux", "ehasteaux": "chasteaux",
    "dudiet": "dudict", "dudicl": "dudict", "dudiel": "dudict", "dudiei": "dudict", "dudil": "dudict",
    "lediet": "ledict", "ledicl": "ledict", "ledil": "ledict", "lediti": "ledict",
    "ladiete": "ladicte", "ladicle": "ladicte", "ladiele": "ladicte", "ladirte": "ladicte",
    "diet": "dict", "dicl": "dict",
    "saincl": "sainct", "sainet": "sainct", "saioct": "sainct", "sainel": "sainct", "saiucl": "sainct",
    "saincle": "saincte", "sainete": "saincte",
    "chaslellainie": "chastellainie", "chastellainic": "chastellainie", "chaslellainic": "chastellainie",
    "chastcllainie": "chastellainie", "chaslcllainic": "chastellainie",
    "prévoslé": "prévosté", "prcvosté": "prévosté", "prévoslez": "prévostez",
    "tordre": "l'ordre", "seavoir": "sçavoir", "sçavoir": "sçavoir",
}
_WORD = re.compile(r"(?<![\w'’-])(" + "|".join(sorted(_WORD_FIXES, key=len, reverse=True)) + r")(?![\w'’])",
                   re.IGNORECASE)


def _fix_word(m: re.Match) -> str:
    word = m.group(1)
    fixed = _WORD_FIXES[word.lower()]
    if word.isupper() and len(word) > 1:
        return fixed.upper()
    return fixed[0].upper() + fixed[1:] if word[0].isupper() else fixed


def fix_ocr(text: str) -> str:
    """Correct the OCR's usual misreadings of common words in this font."""
    return normalize_spaces(_WORD.sub(_fix_word, text))


# A capital H at the start of a name is read as "ll", "Il", "li", "fl" or "11", a capital I as "l".
_NAME_START = [
    (re.compile(r"^(?:ll|Il|li|lI|fl|11|il)(?=[aeiouyàâäéèêëîïôöûü])"), "H"),
    (re.compile(r"^l(?=[^aeiouyàâäéèêëîïôöûü\W])"), "I"),
    (re.compile(r"^[.,'’i]+(?=[A-ZÀ-Ý])"), ""),
]


def fix_name(name: str) -> str:
    """Undo the OCR's misreadings of a place name's first letter ("llagécourt" -> "Hagécourt")."""
    for pattern, repl in _NAME_START:
        name = pattern.sub(repl, name)
    return name
