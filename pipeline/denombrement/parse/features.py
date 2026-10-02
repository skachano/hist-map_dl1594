"""Thematic items without a number: the hautes chaumes (summer pastures of the Vosges).

"Fonyer, en allemand Schinnbsberg, une giste." under "Sous la prévosté de Bruyères": each
chaume with its other names and its number of gîtes (a gîte is forty head of cattle).
The mines (pp. 116-117) are a two-column table with braces that the text layer can't rebuild;
they are left to a reading of the page image.
"""
from __future__ import annotations

import json
import re

from denombrement import config
from denombrement.parse.structure import fold, slug
from denombrement.text import clean

_COUNT = {"une": 1, "un": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8}
_GISTES = re.compile(r",?\s*(?P<n>une|un|deux|trois|quatre|cinq|six|sept|huit)\s+g[iî]s[lt]es?\.?\s*$", re.I)
_PROVOSTSHIP = re.compile(r"^So(?:us|ub)z? la pr[eé]vost[eé] (?:de |d')\s*(?P<x>.+?)\s*$")


def parse_chaumes(lines: list[tuple[str, str]]) -> list[dict]:
    """`lines` holds (page, text) of the chaumes part; returns feature rows."""
    out = []
    provostship = ""
    pending: list[str] = []   # a chaume's name can wrap onto the next line
    page_of_pending = ""
    for page, text in lines:
        text = text.strip()
        if (m := _PROVOSTSHIP.match(text)):
            provostship, pending = clean.fix_name(m.group("x")), []
            continue
        if not provostship:
            continue  # the introduction
        if text.startswith("Fault à noter"):
            break
        pending.append(text)
        page_of_pending = page_of_pending or page
        joined = re.sub(r"^(?:Est la montagne ou chaulme appe\S+ communément|Sont les chaulmes de)\s+", "",
                        clean.dehyphenate(pending))
        m = _GISTES.search(joined)
        if not m:
            continue
        body = joined[: m.start()]
        names = [re.sub(r"^(?:et\s+)?(?:en allemand|ali[aà]s)\s+", "", n.strip(" ,."))
                 for n in re.split(r",\s*|\s+et\s+(?=en allemand|ali[aà]s)", body) if n.strip(" ,.")]
        # "La plaine du Hault-de-Chaulme, en allemand Hobeneck, Schliechlh, quatre gistes": the plain
        # heads the chaumes listed under it; the count belongs to the last one.
        name = clean.fix_name(names[-1] if fold(names[0]).startswith("la plaine") else names[0])
        others = [clean.fix_name(n) for n in names if clean.fix_name(n) != name]
        out.append({
            "id": f"chaume-{slug(name)}", "theme": "chaume", "name": name, "place_id": None,
            "attrs": f"gistes={_COUNT[m.group('n').lower()]}; provostship={provostship}"
                     + (f"; also={'|'.join(others)}" if others else ""),
            "source_page": page_of_pending, "text": joined,
        })
        pending, page_of_pending = [], ""
    return out


def run() -> list[dict]:
    lines = []
    with (config.RAW_DIR / "pages.jsonl").open() as f:
        for raw in f:
            page = json.loads(raw)
            lines += [(page["printed"], l["clean"]) for l in page["body"] if l["part"] == "chaumes"]
    rows = parse_chaumes(lines)
    with (config.EXTRACTED_DIR / "features.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows
