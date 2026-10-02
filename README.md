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
```

## The source PDF

The scan is not in the repository and must never be committed (`pdf/` is git-ignored). Put the
single file `Alix_-_Dénombrement_du_duché_de_Lorraine_en_1594,_1870.pdf` (288 pages, with an
OCR text layer) in `pdf/`. The edition is in the public domain.

## Licence

© 2026 Siargey Kachanovich. The code is under the [MIT License](LICENSE); the data
(`data/curated/`, `data/geometry/`, `web/public/data/`) and the text are under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see [LICENSE-DATA](LICENSE-DATA)). This
does not cover Alix's text and its 1870 edition (public domain), the OpenStreetMap base map (ODbL),
or the Wikidata (CC0) and GeoNames (CC BY 4.0) data, which keep their own terms.
