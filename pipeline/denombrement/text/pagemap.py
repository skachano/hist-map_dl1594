"""Printed page numbers: fixed offsets per range (book.py), checked against the running headers."""
from __future__ import annotations

import re

from denombrement.text import book

# OCR misreadings of digits in the running headers.
_DIGIT = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "i": "1", "!": "1", "|": "1", "H": "11",
                        "S": "5", "s": "5", "G": "6", "b": "6", "B": "8", "z": "2", "Z": "2", "t": "1"})
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def to_roman(n: int) -> str:
    out = ""
    for value, sym in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += sym
            n -= value
    return out


def printed(pdf: int) -> str | None:
    """The printed page label of a PDF page ("VI", "36", "c2" for the corrections), or None."""
    lo, hi = book.ROMAN_PAGES
    if lo <= pdf <= hi:
        return to_roman(pdf + 1)
    lo, hi = book.ARABIC_PAGES
    if lo <= pdf <= hi:
        return str(pdf - book.ARABIC_OFFSET)
    lo, hi = book.CORRECTION_PAGES
    if lo <= pdf <= hi:
        return f"c{pdf - book.CORRECTION_OFFSET}"
    return None


def header_number(header: str) -> str:
    """The digits a running header was read as ("— 4iG —" -> "416"), or roman letters as is."""
    core = re.sub(r"[^\w|!]", "", header)
    if core and set(core.upper()) <= set(_ROMAN):
        return core.upper()
    return re.sub(r"\D", "", core.translate(_DIGIT))


def agrees(header: str, label: str) -> bool | None:
    """Whether a header confirms a page label; None when the header has no number.

    The OCR often reads 3 as 5 and 1 as 4 in this font, so those digits may stand for each other.
    """
    got = header_number(header)
    if not got:
        return None
    want = label.lstrip("c")
    if len(got) != len(want):
        return False
    loose = str.maketrans("53", "33")
    return all(a == b or a.translate(loose) == b.translate(loose) or {a, b} == {"1", "4"}
               for a, b in zip(got, want))
