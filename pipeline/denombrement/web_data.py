"""Stage 7: compile the curated dataset into the files the web app loads.

    data/curated/*.csv, vocab.yaml, names_ja.csv   (Stages 2-5)
    data/geometry/*.geojson                        (Stage 6)
        -> web/public/data/meta.json         source, version, counts, vocabularies (en/fr/de/ja)
        -> web/public/data/places.json       names, type, point, the index's identification, parents
                                             in both hierarchies, tenure and holders, entries
        -> web/public/data/entries.json      the Dénombrement's numbered items, in order, with their text
        -> web/public/data/entities.json     holders: names, type, prominence rank, holdings
        -> web/public/data/features.json     chaumes (summer pastures)
        -> web/public/data/territories.geojson, cells.geojson

The output is deterministic (sorted, no timestamps) and compact: short keys and no empty
fields. The book is in the public domain, so entries keep their full text.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict

from denombrement import config
from denombrement.data import store, validate
from denombrement.data.models import entry_number
from denombrement.text import book

OUT_DIR = config.WEB_DATA_DIR
SIZE_BUDGET = 3_000_000
TENURE_ORDER = ["domain", "fief", "clergy", "safeguard"]
SOURCE = ("Thierry Alix, Dénombrement du duché de Lorraine (1594), éd. H. L. et A. de B., "
          "Recueil de documents sur l'histoire de Lorraine, Nancy, 1870")


def _compact(d: dict) -> dict:
    """Drop None, empty strings/lists/dicts and False flags; keys keep their order."""
    return {k: v for k, v in d.items() if not (v is None or v is False or (isinstance(v, (str, list, dict)) and not v))}


def _dump(name: str, data) -> int:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (OUT_DIR / name).write_text(text + "\n")
    return len(text.encode()) + 1


def _attrs(text: str | None) -> dict:
    """"gistes=2; provostship=Arches; also=A|B" -> {"gistes": 2, "provostship": "Arches", "also": ["A", "B"]}."""
    out: dict = {}
    for part in (text or "").split(";"):
        key, _, value = part.strip().partition("=")
        if not key:
            continue
        if "|" in value:
            out[key] = value.split("|")
        elif value.isdigit():
            out[key] = int(value)
        else:
            out[key] = value
    return out


def build() -> dict[str, int]:
    ds = store.load()
    errors = [i for i in validate.validate(ds) if i.level == "error"]
    if errors:
        raise SystemExit(f"refusing to build web data: {len(errors)} validation error(s); run `make validate`")

    ja_file = config.CURATED_DIR / "names_ja.csv"
    ja = {r["id"]: r["name_ja"] for r in csv.DictReader(ja_file.open(newline=""))} if ja_file.exists() else {}

    parents: dict[str, list[dict]] = defaultdict(list)
    for _, m in sorted(ds.memberships, key=lambda lm: (lm[1].child_id, lm[1].relation, lm[1].parent_id)):
        parents[m.child_id].append(_compact({"id": m.parent_id, "rel": m.relation, "share": m.share}))

    # A place's entries: those matched to it, and those the index sends it to (an entry can name
    # several places); its spellings by source, each with the entries it stands for.
    entry_by_no = {e.no: e for _, e in ds.entries}
    entries_of: dict[str, list[int | str]] = defaultdict(list)
    also: dict[str, list[str]] = defaultdict(list)
    for _, e in ds.entries:
        if e.place_id:
            entries_of[e.place_id].append(entry_number(e.no) or e.no)
    index_of: dict[str, dict[str, list]] = defaultdict(dict)
    for _, x in sorted(ds.index_links, key=lambda lx: (lx[1].place_id, entry_number(lx[1].entry_no) or 0)):
        no = entry_number(x.entry_no) or x.entry_no
        if no not in entries_of[x.place_id]:
            entries_of[x.place_id].append(no)
            also[x.entry_no].append(x.place_id)
        # the numbers the index gives for the spelling: not those it doesn't print on that line
        nos = index_of[x.place_id].setdefault(x.index_name, [])
        if "number not printed" not in (x.notes or ""):
            nos.append(no)
    for nos in entries_of.values():
        nos.sort(key=lambda n: n if isinstance(n, int) else 0)
    # an entry's lines in the editor's index (pp. 183-262) that print its number, with their page
    # An entry no line prints still shows the line of its place, marked "np" (number not printed).
    index_lines: dict[str, list[dict]] = defaultdict(list)
    unprinted: dict[str, list[dict]] = defaultdict(list)
    of_place: dict[str, list[dict]] = defaultdict(list)
    for _, x in ds.index_links:
        page = x.source_page if str(x.source_page or "").isdigit() and int(x.source_page) >= book.INDEX_PRINTED[0] else None
        line = _compact({"s": x.index_name, "p": page, "place": x.place_id})
        if "number not printed" in (x.notes or ""):
            unprinted[x.entry_no].append({**line, "np": True})
        else:
            index_lines[x.entry_no].append(line)
        if page and line not in of_place[x.place_id]:
            of_place[x.place_id].append(line)
    for _, e in ds.entries:
        if e.series == "main" and not index_lines.get(e.no):
            index_lines[e.no] = unprinted.get(e.no) or [{**x, "np": True} for x in of_place.get(e.place_id or "", [])[:1]]

    def spellings(p) -> list[dict]:
        book: dict[str, list] = {}
        for no in entries_of.get(p.id, []):
            e = entry_by_no.get(str(no))
            if e is not None:
                book.setdefault(e.name, []).append(no)
        return ([{"s": s, "src": "book", "e": nos} for s, nos in book.items()]
                + [{"s": s, "src": "index", "e": nos} for s, nos in index_of.get(p.id, {}).items()]
                + [{"s": s, "src": "old"} for s in p.old_forms])

    holdings_of: dict[str, list[dict]] = defaultdict(list)
    holdings_by_holder = Counter()
    for _, h in sorted(ds.holdings, key=lambda lh: (lh[1].place_id, TENURE_ORDER.index(lh[1].tenure),
                                                     lh[1].holder_id or "")):
        holdings_of[h.place_id].append(_compact({
            "t": h.tenure, "h": h.holder_id, "share": h.share, "with": sorted(h.share_with),
            "e": [entry_number(n) or n for n in h.via_entry]}))
        if h.holder_id:
            holdings_by_holder[h.holder_id] += 1

    def main_tenure(pid: str) -> str | None:
        """Domain if any entry is domain, else fief, else clergy, else safeguard."""
        tenures = {h["t"] for h in holdings_of.get(pid, [])}
        return next((t for t in TENURE_ORDER if t in tenures), None)

    places = []
    for _, p in sorted(ds.places, key=lambda lp: lp[1].id):
        territory = p.kind == "territory"
        places.append(_compact({
            "id": p.id, "kind": p.kind, "type": p.place_type,
            "name": _compact({"fr": p.name_fr, "de": p.name_de, "en": p.name_en, "ja": ja.get(p.id)}),
            "spell": spellings(p) if not territory else None,
            "variants": sorted(v for v in p.variants if v != p.name_fr) if territory else None,
            "index": _compact({"kind": p.index_kind, "commune": p.index_commune, "canton": p.index_canton,
                               "dept": p.index_dept}),
            "lat": p.lat, "lon": p.lon,
            # how sure the point is (high / medium / low); "approx" = placed at its commune
            "geo": p.geo_confidence if p.lat is not None and not territory else None,
            "approx": p.geo_method == "approximate",
            "lost": p.lost,
            "wd": p.wikidata_id, "country": p.modern_country,
            "h": p.hierarchy, "holder": sorted(p.holder_id), "counterpart": p.counterpart_id,
            "basis": p.counterpart_basis,
            "parents": parents.get(p.id, []),
            "tenure": main_tenure(p.id),
            "hold": holdings_of.get(p.id, []),
            "entries": entries_of.get(p.id, []),
            "pages": p.source_page,
            "conf": None if p.confidence == "high" else p.confidence,
        }))

    entries = [_compact({
        "no": entry_number(e.no) or e.no, "text": e.text, "name": e.name, "desc": e.descriptors,
        "district": e.district_id, "realm": e.realm_id, "section": e.section,
        "holders": e.holder_id, "share": e.share, "with": e.share_with,
        "series": None if e.series == "main" else e.series, "order": e.order, "place": e.place_id,
        "also": also.get(e.no), "ix": index_lines.get(e.no),
        "page": e.source_page, "conf": None if e.confidence == "high" else e.confidence,
    }) for _, e in ds.entries]  # the book's order

    ranked = sorted((e for _, e in ds.entities), key=lambda e: (-holdings_by_holder[e.id], e.id))
    entities = [_compact({
        "id": e.id, "type": e.entity_type,
        "name": _compact({"en": e.name_en, "fr": e.name_fr, "de": e.name_de, "ja": ja.get(e.id)}),
        "rank": rank, "holdings": holdings_by_holder[e.id],
    }) for rank, e in enumerate(ranked, start=1)]
    entities.sort(key=lambda e: e["id"])

    features = [_compact({
        "id": f.id, "theme": f.theme, "name": f.name, "place": f.place_id, "attrs": _attrs(f.attrs),
        "page": f.source_page}) for _, f in ds.features]   # the book's order

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sizes = {
        "places.json": _dump("places.json", places),
        "entries.json": _dump("entries.json", entries),
        "entities.json": _dump("entities.json", entities),
        "features.json": _dump("features.json", features),
    }
    for name in ("territories.geojson", "cells.geojson"):
        shutil.copyfile(config.DATA_DIR / "geometry" / name, OUT_DIR / name)
        sizes[name] = (OUT_DIR / name).stat().st_size

    digest = hashlib.sha256()
    for name in sorted(sizes):
        digest.update((OUT_DIR / name).read_bytes())
    vocab = {name: {k: {lang: v[lang] for lang in ("en", "fr", "de", "ja") if v.get(lang)}
                    | ({"hierarchy": v["hierarchy"]} if v.get("hierarchy") else {})
                    for k, v in terms.items()}
             for name, terms in ds.vocab.items()}
    meta = {
        "year": config.YEAR,
        "source": SOURCE,
        "version": digest.hexdigest()[:12],  # changes whenever any data file changes
        "counts": {
            "entries": len(entries), "places": len(places),
            "settlements": sum(p["kind"] == "settlement" for p in places),
            "territories": sum(p["kind"] == "territory" for p in places),
            "located": sum(1 for p in places if p["kind"] == "settlement" and "lat" in p),
            "entities": len(entities), "features": len(features),
            "areas": _count_features(OUT_DIR / "territories.geojson"),
        },
        "vocab": vocab,
    }
    sizes["meta.json"] = _dump("meta.json", meta)
    total = sum(sizes.values())
    for name, size in sorted(sizes.items()):
        print(f"  {name:22} {size / 1000:7.1f} kB")
    print(f"  total {total / 1e6:.2f} MB (budget {SIZE_BUDGET / 1e6:.2f} MB) -> {OUT_DIR.relative_to(config.ROOT)}/")
    if total > SIZE_BUDGET:
        print("  WARNING: over the size budget")
    return sizes


def _count_features(path) -> int:
    return len(re.findall(r'"type":"Feature"', path.read_text()))
