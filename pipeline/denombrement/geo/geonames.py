"""GeoNames populated places (and castles, abbeys, localities) in the region, from the free
country dumps: hamlets and farms that Wikidata often lacks."""
from __future__ import annotations

import csv
import io
import zipfile

import requests

from denombrement import config
from denombrement.geo.wikidata import BBOX, HEADERS

DUMP_DIR = config.RAW_DIR / "geo_cache" / "geonames"
COUNTRIES = ("FR", "DE", "LU")
FEATURES = {("P", None), ("S", "CSTL"), ("S", "MSTY"), ("S", "ABBY"), ("L", "LCTY"), ("S", "RUIN"), ("S", "FRM")}


def _download(country: str) -> bytes:
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    path = DUMP_DIR / f"{country}.zip"
    if not path.exists():
        r = requests.get(f"https://download.geonames.org/export/dump/{country}.zip", headers=HEADERS, timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path.read_bytes()


def region() -> list[dict]:
    out = []
    for country in COUNTRIES:
        with zipfile.ZipFile(io.BytesIO(_download(country))) as z:
            text = io.TextIOWrapper(z.open(f"{country}.txt"), encoding="utf-8")
            for row in csv.reader(text, delimiter="\t", quoting=csv.QUOTE_NONE):
                lat, lon = float(row[4]), float(row[5])
                if not (BBOX["south"] < lat < BBOX["north"] and BBOX["west"] < lon < BBOX["east"]):
                    continue
                if (row[6], None) not in FEATURES and (row[6], row[7]) not in FEATURES:
                    continue
                names = {row[1], row[2], *filter(None, row[3].split(","))}
                out.append({"geonameid": int(row[0]), "name": row[1], "lat": lat, "lon": lon, "country": country,
                            "feature": f"{row[6]}.{row[7]}", "names": {n for n in names if n}})
    return out
