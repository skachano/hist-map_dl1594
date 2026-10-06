# Duchy of Lorraine in 1594 — Dénombrement Atlas

Interactive map of the Duchy of Lorraine as Thierry Alix described it in his *Dénombrement du
duché de Lorraine* (1594): its administrative divisions and feudal realms, and whether each
place was ducal domain, a fief or church land. Based on the 1870 edition (*Recueil de documents
sur l'histoire de Lorraine*, Société d'archéologie lorraine). See [doc/Plan.md](doc/Plan.md).

A partial copy of [hist_map](../hist_map) (the bailliage d'Allemagne 1600–1632), cut down to the
information this book contains: a single date, so no year slider.

Everything runs in Docker (rootless Docker works without extra config).

```sh
cp .env.example .env   # add ANTHROPIC_API_KEY (needed from Stage 3)
make build             # build images
make dev               # http://localhost:5174
make test              # pytest + vitest
make info              # paths and the source PDF
make extract           # Stage 1: PDF -> data/raw/ (page text, parts, index, old forms, corrections)
make validate          # Stage 2: check data/curated/ against the schema and vocab.yaml
make schema            # Stage 2: export JSON Schemas to data/schema/
make parse             # Stage 3: parse the Dénombrement -> data/extracted/ (+ parse_report.md)
make curate            # Stage 4: data/curated/*.csv + data/review/report.md (edit rules.yaml, manual/)
make geocode           # Stage 5: coordinates + modern names (Wikidata, GeoNames), then run make curate
make geometry          # Stage 6: settlement cells + territory areas -> data/geometry/
make data              # parse, curate, geocode, curate, geometry: the whole chain
```

Geocoding downloads Wikidata's settlements in the region (cached in `data/raw/geo_cache/`) and
the GeoNames dumps for FR, DE and LU. It also uses hist_map's checked geocoding of the bailliage
d'Allemagne when it is there:
`cp ../hist_map/data/curated/geocoding.csv data/raw/geo_cache/hist_map_geocoding.csv`.

`make dicotopo` (a prototype) matches garbled and unlocated names against the dated old spellings
of the [Dictionnaire topographique de la France](https://dicotopo.cths.fr) (Meurthe, Meuse,
Moselle, Vosges; cached in `data/raw/geo_cache/dicotopo/`) and writes suggestions to
`data/review/dicotopo.md`. It reads entries checked by hand from `data/review/manual-check.md`
(git-ignored) when it is there.

## Deployment

`.github/workflows/pages.yml` publishes the atlas on GitHub Pages on every push to `main`: it runs
the pipeline tests, compiles `web/public/data/` from the committed `data/curated/` and
`data/geometry/` (the scan and `data/raw/` are not needed), runs the web tests, builds the app under
`/<repository name>/` and deploys `web/dist/`. One-time setup: Settings → Pages → Source:
GitHub Actions.

## The source PDF

The scan is not in the repository and must never be committed (`pdf/` is git-ignored). Put the
single file `Alix_-_Dénombrement_du_duché_de_Lorraine_en_1594,_1870.pdf` (288 pages, with an
OCR text layer) in `pdf/`. The edition is in the public domain.

## Licence

© 2026 Siargey Kachanovich. The code is under the [MIT License](LICENSE); the data
(`data/curated/`, `data/geometry/`, `web/public/data/`) and the text are under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see [LICENSE-DATA](LICENSE-DATA)). This
does not cover Alix's text and its 1870 edition (public domain), the OpenStreetMap base map (ODbL),
or the Wikidata (CC0), GeoNames (CC BY 4.0) and DicoTopo (Licence Ouverte 2.0) data, which keep
their own terms. DicoTopo: *Dictionnaire topographique de la France*, CTHS, École nationale des
chartes and Archives nationales, <https://dicotopo.cths.fr>, data downloaded on 5 October 2026.
