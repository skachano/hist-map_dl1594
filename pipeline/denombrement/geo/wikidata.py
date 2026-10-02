"""Every settlement Wikidata has in the region, downloaded once by tiles and cached.

The places' names are the index's OCR spellings ("Picrrevillc"), so instead of asking Wikidata
for exact labels (hist_map's approach) the whole region is downloaded and matched locally.
"""
from __future__ import annotations

import hashlib
import json
import time

import requests

from denombrement import config

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "hist-map-dl1594/0.1 (historical atlas research project; python-requests)",
           "Accept": "application/sparql-results+json"}
CACHE_DIR = config.RAW_DIR / "geo_cache" / "wikidata"
# Lorraine, the Vosges, the Saarland, the Palatinate and the edges of Alsace and Luxembourg.
BBOX = {"west": 5.3, "east": 7.8, "south": 47.8, "north": 50.0}
TILE = 0.5
COUNTRIES = {"Q142": "FR", "Q183": "DE", "Q32": "LU"}

SETTLEMENT_CLASSES = {
    "Q484170",    # commune of France
    "Q26714626",  # former commune of France
    "Q2989454",   # associated commune of France
    "Q262166",    # municipality of Germany
    "Q116457956", "Q42744322", "Q15632617",  # German municipality variants
    "Q253019",    # Ortsteil
    "Q2785216",   # municipal district
    "Q123705",    # neighbourhood
    "Q486972", "Q532", "Q5084", "Q3957", "Q515", "Q1549591", "Q3257686",  # settlement, village, hamlet, town…
    "Q2919801", "Q1637706",  # commune / locality of Luxembourg
    "Q1133961",   # deserted medieval village
}
CASTLE_ABBEY_CLASSES = {"Q23413", "Q751876", "Q160742", "Q44613", "Q1070990"}

_QUERY = """
SELECT ?item ?lat ?lon ?inst ?country ?fr ?de ?en ?ja WHERE {
  SERVICE wikibase:box { ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point(%f %f)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point(%f %f)"^^geo:wktLiteral . }
  ?item wdt:P31 ?inst .
  VALUES ?inst { %s }
  BIND(geof:latitude(?coord) AS ?lat) BIND(geof:longitude(?coord) AS ?lon)
  OPTIONAL { ?item wdt:P17 ?country }
  OPTIONAL { ?item rdfs:label ?fr FILTER(lang(?fr) = "fr") }
  OPTIONAL { ?item rdfs:label ?de FILTER(lang(?de) = "de") }
  OPTIONAL { ?item rdfs:label ?en FILTER(lang(?en) = "en") }
  OPTIONAL { ?item rdfs:label ?ja FILTER(lang(?ja) = "ja") }
}
"""


def _run(query: str) -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / (hashlib.sha1(query.encode()).hexdigest()[:20] + ".json")
    if path.exists():
        return json.loads(path.read_text())
    for attempt in range(6):
        r = requests.post(ENDPOINT, data={"query": query}, headers=HEADERS, timeout=180)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(int(r.headers.get("Retry-After", 15 * (attempt + 1))))
            continue
        r.raise_for_status()
        rows = r.json()["results"]["bindings"]
        path.write_text(json.dumps(rows, ensure_ascii=False))
        time.sleep(1)  # be polite to the public endpoint
        return rows
    r.raise_for_status()
    return []


def region() -> dict[str, dict]:
    """{qid: {qid, lat, lon, types, country, fr, de, en, ja}} for the whole bounding box."""
    values = " ".join(f"wd:{c}" for c in sorted(SETTLEMENT_CLASSES | CASTLE_ABBEY_CLASSES))
    items: dict[str, dict] = {}
    lon = BBOX["west"]
    while lon < BBOX["east"]:
        lat = BBOX["south"]
        while lat < BBOX["north"]:
            q = _QUERY % (lon, lat, min(lon + TILE, BBOX["east"]), min(lat + TILE, BBOX["north"]), values)
            for row in _run(q):
                qid = row["item"]["value"].rsplit("/", 1)[-1]
                it = items.setdefault(qid, {"qid": qid, "lat": float(row["lat"]["value"]),
                                            "lon": float(row["lon"]["value"]), "types": set(), "country": None,
                                            "fr": None, "de": None, "en": None, "ja": None})
                it["types"].add(row["inst"]["value"].rsplit("/", 1)[-1])
                if "country" in row:
                    it["country"] = COUNTRIES.get(row["country"]["value"].rsplit("/", 1)[-1], it["country"])
                for lang in ("fr", "de", "en", "ja"):
                    if lang in row and not it[lang]:
                        it[lang] = row[lang]["value"]
            lat += TILE
        lon += TILE
    return items
