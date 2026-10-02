# Duchy of Lorraine in 1594 — Dénombrement Atlas (Plan)

## 1. Context & goal
This is an interactive web app that maps the Duchy of Lorraine as Thierry Alix, president of the Chambre des Comptes, described it in his *Dénombrement du duché de Lorraine* (1594). It shows which bailliage, prévôté and ban each town, village, castle and abbey belonged to, and whether it was ducal domain, a fief or a church holding. The only source is the 1870 edition, found in `pdf/`:

> *Description particulière des duché de Lorraine, comtez et seigneuries en dépendantes, et notamment du comté de Bitche*, par Thierry Alix. In *Recueil de documents sur l'histoire de Lorraine*, Société d'archéologie lorraine, Nancy 1870. The edition and its two tables were made by the editors who sign the introduction "H. L. et A. de B."

The PDF is a 288-page scan with an OCR text layer (iLovePDF, Times/Helvetica, unembedded). The layer is usable but noisy: digits are misread (`577.` for 377, `1555.` for 1553), and so are letters (`ebasteau` for *chasteau*, `Saincl` for *Sainct*).

### The book
Printed page = PDF page − 11 for the main text and the tables. The introduction uses roman numerals, and the corrections have their own numbering.

| PDF pages | printed | content | use |
|---|---|---|---|
| 4–13 | I–XIV | editor's introduction: the duchy's extent, later losses and reorganisations (1698, 1751), the Barrois (which the Dénombrement leaves out), the manuscripts | About page, notes |
| 14–17 | 3–6 | Alix's table of contents: every bailliage and its prévôtés, châtellenies, terres | skeleton of the hierarchy |
| 20–44 | 9–33 | dedication; fables about the origin of the duchy; "singularitez" of the duchy | not mapped |
| 45–46 | 34–35 | the duchy is made of 8 bailliages, 4 counties, and 13 towns and châtellenies outside the bailliages | top of the hierarchy |
| 46–127 | 35–116 | **the Dénombrement proper**: entries **1–~2293**, numbered by the editor, under headings for bailliage → prévôté/office/terre → ban/mairie/val, each split into *Domaine*, *Fiedvez* (fiefs) and *Clergé*, plus the safeguards | core data |
| 127–128 | 116–117 | silver, lead, copper and azure mines (Val de Lièpvre, Bussang, Le Thillot, Wallerfangen); gemstones in the office of Schaumburg | thematic layer |
| 128–131 | 117–120 | the *hautes chaumes*: summer pastures in the Vosges, each with its number of *gîtes* (×40 cattle) | thematic layer |
| 131–138 | 120–127 | rivers rising in the duchy and the places along their courses | thematic layer (later) |
| 138–145 | 127–134 | **thematic lists, numbered on to ~2447**: towns and bourgs, cathedral and collegiate churches, abbeys of monks and of nuns by order, priories, commanderies, the Charterhouse | place attributes |
| 145–182 | 134–171 | Latin verse; the county of Bitche: discourse, boundary walk, villages, forests, coinage, measures | Bitche detail; boundary as a later layer |
| 183–185 | 172–174 | how the editor's tables were made, and abbreviations | parser rules |
| 186–193 | 175–182 | **table of old forms** (old spelling → modern name) | variants |
| 194–273 | 183–262 | **table of place names**: modern name, kind (vil., ham., ferme, anc. abbaye…), commune, canton, département or state, and the entry numbers; unidentified old names in italics | identification and geocoding |
| 274–275 | 263–264 | table of contents of the volume | — |
| 276–285 | 1–10 | **corrections** to the text and the tables | apply before curation |

Sample index line: `Beckingen, vil. (commanderie), com. de Haustadt, canton de Merzig, 1450, 2485.` Entry numbers in the index are abbreviated: `1475, 1537, 38` means 1538, and `709-715` is a range.

### What the book says, and what it doesn't
It is a **single snapshot** around 1594. Marsal is "added", which dates the text to 1594–95. There are no dates for individual facts, no transfers, no rulers and no disputes. For each place, the information is:
- **its units**, of two different natures that the headings mix:
  - **administrative divisions** of the duke's government: bailliage → prévôté, châtellenie, office, recette → ban, mairie, val
  - **feudal realms**, i.e. lands held as a title or lordship: comté, marquisat, baronnie, terre, seigneurie, fief, and the villages of an abbey ("de laquelle dépendent les villages cy-après")

  A heading can name one ("Le ban de Sept"), the other ("Terre de Pierrefort") or both at once ("Prévosté, terre et seigneurie de Deneuvre", "Bailliage du comté de Vaudémont"). Feudal realms answer to a district for homage and aids: under the prévôté of Nancy "pour l'esgard des fiedz, foid, hommages et aydes extraordinaires, dépendent les terres … le comté de Challigny, terres de L'avantgarde, du Chastelet, de Pierrefort et de Hey". Some places sit in two units ("Azerailles, en partie").
- **its tenure**: *Domaine* of His Highness, *Fiedvez* (a fief, sometimes with the vassal named in the heading: "tenu en fief … par les sieurs comtes d'Eberstein et Oberstein"), *Clergé*, a ducal *sauvegarde* over another lord's villages ("Villages du chapitre de Toul qui sont des sauvegardes de Son Altesse"), a share ("pour la moitié contre les sieurs comtes de la Roche", "pour une partie contre les chanoines de Fénestrange").
- **its kind**, from the short description after the name: ville, bourg, village, hameau, chasteau, cense, gagnage, abbaye, prieuré, verrerie, saline, moulin… An entry can carry several of them ("chasteau, ville et église collégiale").
- **its place in the thematic lists**: town, cathedral, collegiate church, abbey (with its order), priory, commandery, mine, chaume.

### Decisions taken
- **A partial copy of hist_map.** The pipeline, the Docker/Make setup, the geocoder, the geometry and the web app are copied from `../hist_map` and cut down to the information this book has. There are no shared packages, so each project can change on its own. Code that is copied unchanged keeps its structure, so fixes can be ported by hand.
- **No time dimension.** There is no year slider, no events, no rulers, no timelines, no Changes view and no Disputes view. Everything else that depends on a year (`snapshot(year)`, membership periods, territory versions) becomes a fixed state.
- **Administrative divisions and feudal realms are separate hierarchies.** Every territory record belongs to exactly one of them. **When an administrative unit and a feudal realm cover the same land, both are recorded**, as two territories with the same members, linked as counterparts: e.g. the prévôté of Deneuvre (administrative) and the lordship of Deneuvre (feudal), or the office of Schaumburg and the lordship of Schaumburg. This holds whether the heading names both or only one of them (§2, *Coinciding territories*). This differs from hist_map, which merges "office, lordship, county… of X" into one territory and only derives the admin/feudal split in the Territories view from the type.
- **Parse first, LLM second.** Most of the list is regular enough for a deterministic parser: numbers, headings, *Domaine/Fiedvez/Clergé*. The Claude API is used only for what the parser cannot settle: headings that name holders or shares, and the prose sections (mines, chaumes, Bitche).
- **The editor's index is the identification.** Each numbered entry is matched to a modern place through the index, not through spelling. The index is OCR'd too, so it doubles as a second reading of each name.
- **Copyright:** the 1870 edition is in the public domain. The extracted text, full entry texts and quotes can be committed and shown in the app. The PDF itself is never committed: `pdf/` is git-ignored, as in hist_map, and the README says where to get the scan and where to put it.
- **Environment and frontend:** the same as hist_map: everything runs in Docker; Vite + TypeScript + MapLibre GL, a static SPA, deployed to GitHub Pages; UI languages EN/FR/DE/JA.

## 2. Data model
IDs are slugs (`saint-avold`, `provostship-dompaire`). Territory ids are `<territory type>-<seat>`, with the type's vocabulary key (`provostship-deneuvre`, `lordship-deneuvre`), so that counterparts share their seat. Every fact carries `source_page` (printed page), `confidence` (high/medium/low) and `notes`. CSV conventions are the same as in hist_map: list cells are `|`-separated, and `source_page` looks like `49`, `50-52` or `14;131`.

The key change from hist_map is that **a numbered entry is not a place**. One village can appear under several numbers: in two prévôtés, as part domain and part fief, and again in the thematic lists. So entries and places are separate tables.

### `entries`: the book's numbered items (generated, then corrected)
| field | description |
|---|---|
| `no` | the editor's number (1–2487); unnumbered items get `x-<page>-<n>` |
| `text` | the entry as printed, OCR-corrected ("Hombourg, chasteau, ville et église collégiatte Sainct-Estienne") |
| `name` | the name part ("Hombourg") |
| `descriptors[]` | vocabulary keys from the description (`castle`, `town`, `collegiate_church`) |
| `district_id` | the administrative division it stands under (FK to `places`), from the nearest administrative heading |
| `realm_id` | the feudal realm it stands under (FK to `places`), from the nearest feudal heading; empty when there is none |
| `section` | `domain`, `fief`, `clergy`, `safeguard`, `other` (from the sub-heading) |
| `holder_id[]` | the holder named in the heading or the entry (FK to `entities`); empty for domain = the duke |
| `share` | `part` ("en partie"), `1/2` ("pour la moitié contre"), `joint` (co-holders named together without shares), or empty |
| `share_with[]` | the other party in a share (FK to `entities`) |
| `series` | `main` for the Dénombrement; `towns`, `cathedrals`, `collegiates`, `abbeys_m`, `abbeys_f`, `convents_f`, `grey_sisters`, `other_sisters`, `priories`, `friaries`, `convents_m`, `commanderies`, `charterhouses` for the thematic lists |
| `order` | religious order for abbeys and priories (Benedictine, Premonstratensian, Cistercian…) |
| `place_id` | the resolved place (FK to `places`), or empty when unidentified |
| `source_page`, `confidence`, `notes` | |

### `places`: settlements and territories
The same columns as hist_map's `places.csv`: `id`, `kind` (`settlement` / `territory`), `name_fr/de/en`, `variants[]` (the book's spellings and the old forms table), `place_type`, `lat`, `lon`, `wikidata_id`, `geonames_id`, `modern_country`, `source_page`, `confidence`, `notes`. Columns added:
- `index_kind`, `index_commune`, `index_canton`, `index_dept`: the index's identification, kept as written in 1870
- `lost`: the place no longer exists or could not be identified (italics in the index)
- for territories only:
  - `hierarchy`: `admin` or `feudal`, set by the territory type
  - `holder_id[]`: who holds a feudal realm (the duke for the counties of Vaudémont, Blâmont and Bitche, a vassal or a church body otherwise; co-holders together, as for Keltern-Ostern); empty for administrative divisions
  - `counterpart_id`: the territory of the other hierarchy that covers the same land (prévôté of Deneuvre ↔ lordship of Deneuvre), so the app can link them
  - `counterpart_basis`: why the pair exists: `heading`, `slot`, `alix_list` or `rule` (see below)

The territories are:
- **administrative**: the duchy, the 8 bailliages, prévôtés, châtellenies, offices, recettes, the Landschultheisserei and sous-prévôté of Sierck, bans, mairies, vals
- **feudal**: the 4 counties (Vaudémont, Blâmont, Bitche, Chaligny), terres, seigneuries, baronnies, named fiefs, and church temporalities (the villages of the abbey of Saint-Avold)

The towns and châtellenies "qui ne sont de bailliages" (Sarrebourg, Phalsbourg, Hombourg, Saint-Avold, Marsal…) are administrative divisions directly under the duchy.

### Coinciding territories
When an administrative unit and a feudal realm are the same land, both are recorded, with a counterpart link between them. The pipeline creates a pair from any one of these sources, recorded in `counterpart_basis`:
- `heading`: the heading names both ("Prévosté, terre et seigneurie de Deneuvre", "Bailliage du comté de Vaudémont", "Les chastellainies, terres et seigneuries de Hombourg et Sainct-Avol").
- `slot`: a feudal heading stands where a division would, with entries directly under it and no division in between. "Terre et seigneurie de Faulquemont" sits directly under the bailliage d'Allemagne, so it is also an administrative division of that bailliage. "Comté de Blamont" sits outside the bailliages, so it is also a division directly under the duchy.
- `alix_list`: Alix's own list of the duchy's parts (p. 34) names it as a province, county, or one of the "villes et chastellenies … qui ne sont pas de bailliages".
- `rule`: a pair declared by hand in `rules.yaml` after review, with its source (the editor's notes, the introduction, or a reference work), e.g. an office that the book only calls an office but that was the duke's lordship (`office-schaumburg ↔ lordship-schaumburg`).

The two records of a pair:
- **members:** by default, the same settlements. The village links (`admin` and `feudal`) are generated for both from the same entries. An entry that the book places in only one of them ("en partie", or a fief inside the office that is not part of the lordship) makes the member sets differ. The report lists every such difference.
- **links between them:** the realm's `ressort` is its counterpart division.
- **holder:** the realm records its holder (the duke for domain lands); the division has no holder.
- **geometry:** the same area when the members are the same.

A realm that lies inside a division without covering all of it (the terre of Pierrefort in the prévôté of Nancy) is not a pair. It stays a feudal realm with a `ressort`.

### `memberships`: the two hierarchies
`child_id`, `parent_id`, `relation`, `share` (`part` when the book says "en partie"), `source_page`. There are no years. A place may have several parents. `relation` is one of:
- `admin`: a settlement or division lies in an administrative division (village → ban → prévôté → bailliage → duchy)
- `feudal`: a settlement or realm is part of a feudal realm (village → lordship; lordship → county when the book says so)
- `ressort`: a feudal realm answers to an administrative division for homage, aids and justice (county of Chaligny → prévôté of Nancy)

The validator also checks that counterparts point at each other, are of opposite hierarchies and share a seat, and it reports member sets that differ within a pair. The validator checks that `admin` links only administrative territories, `feudal` only feudal ones, and `ressort` goes from a feudal realm to an administrative division. Every settlement must reach the duchy through `admin` links, or through a realm's `ressort`. A settlement listed only under a feudal heading ("Terre de Pierrefort") takes its district from the realm's `ressort`, and is flagged when there is none.

### `entities`: holders
`id`, `name_en/fr/de`, `entity_type`, `color`, `source_page`, `notes`. Entity types:
- the duke ("Vostre Altesse", `duchy-lorraine`)
- fief holders: houses and persons ("les sieurs comtes d'Eberstein", "le sieur de Haussonville")
- church bodies: chapters, abbeys, priories, commanderies
- neighbours named in shares: the bishops and chapters of Metz, Toul and Verdun, the counts of La Roche, the Rhine counts…

There is no `rulers` table: the book names holders, not reigns.

### `holdings`: tenure per place (generated from `entries`)
`place_id`, `tenure` (`domain`, `fief`, `clergy`, `safeguard`), `holder_id`, `share`, `share_with[]`, `via_entry[]`, `source_page`. This replaces hist_map's `rights`: a single dimension (tenure) instead of right types, and no periods.

### `features`: thematic items without a number
`id`, `theme` (`mine`, `chaume`, `river`, `gem`), `name`, `place_id` (where it is), `attrs` (metals; gîtes; the places along a river), `source_page`.

### `vocab.yaml`
Labels in EN/FR/DE/JA for (also `relations`, `counterpart_bases`, `sections`, `series` and `feature_themes`):
- `place_types`: hist_map's list plus cense, gagnage, verrerie, saline, mine, chaume, priory, commandery, collegiate church, chartreuse
- `territory_types`, each with its hierarchy:
  - administrative: bailliage, prévôté, sous-prévôté, châtellenie, office, recette, Landschultheisserei, ban, mairie, val
  - feudal: comté, marquisat, baronnie, terre, seigneurie, fief, franc-alleu, temporel (church lands)
- `tenures`, `entity_types`, `religious_orders`, `confidence`

### Derived data (not stored)
- Each place's administrative chain up to the duchy, or more than one chain when it is split.
- Its feudal chain, when it lies in a realm: lordship → county, with the holder of each.
- Its main tenure: domain if any entry is domain, else fief, else clergy.

## 3. App screens
All screens share the UI language switch (EN/FR/DE/JA, which changes both labels and place names) and the place panel. There is no year bar.

1. **Map** (default): settlement cells and points, coloured by one of these:
   - **tenure**: domain / fief / clergy, with safeguard and other tenures in grey (three validated CVD-safe colours plus grey, as in hist_map)
   - **holder**: the legend picks which holders get the three colours, as in hist_map
   - **district**: bailliage areas with white borders and labels instead of eight colours
   - **realm**: places inside a named feudal realm, coloured by the kind of realm (county, lordship/terre, church temporality), and the rest in grey

   Hatching marks shared places ("en partie", "pour la moitié"). Places outside the duchy that the book doesn't list (the Three Bishoprics, the Barrois) are left blank and labelled.
2. **Territories:** hist_map's Territories view without the year, with a switch between the two hierarchies (`#/territories?h=admin|feudal&lvl=…`):
   - **Administrative divisions:** level 1 = bailliages and the towns outside them; level 2 = prévôtés, châtellenies, offices; level 3 = bans, mairies, vals; 0 = all levels. Areas tile the duchy.
   - **Feudal realms:** level 1 = realms held directly (counties, terres, lordships, church temporalities); level 2 = realms inside them; 0 = all. Areas cover only the realms' members, so the land between them is blank. Each realm is coloured by kind, and its tooltip gives its holder and the district it answers to.

   The panel lists a territory's members in the book's order with their numbers. It links a territory to its counterpart in the other hierarchy (prévôté of Deneuvre ↔ lordship of Deneuvre), and a feudal realm to its `ressort`.
3. **Holders:** pick a holder (a fief-holding house, a chapter, an abbey) to see everything it holds on the map and in a list. hist_map's entity view, without rulers or gains and losses.
4. **Place panel:**
   - names in four languages and the book's spellings
   - the index's identification (commune, canton, département in 1870)
   - every entry that names the place, with its number, full text and page
   - two clickable chains: the administrative one ("District") and the feudal one ("Realm"), when it has one
   - its tenure and holder
   - its thematic entries: town, abbey and order, mine, chaume, river
5. **Table:** every numbered entry: number, text, modern place, district, realm, tenure, holder and page. It can be filtered by district, realm, tenure, holder and list, and exported to CSV. This is where you read the Dénombrement in order.
6. **Church & resources:** layers from the thematic lists:
   - cathedrals, collegiate churches, abbeys (by order), priories, commanderies
   - towns and bourgs
   - mines and chaumes

   Rivers come later, drawn from OSM waterways with the places the book lists along each one.
7. **About & sources:** the book and edition, the editor's introduction in short, what the map shows and its conventions, how the data was made, the copyright and attributions.

Dropped from hist_map: the year bar and play control, the right-type tabs, Disputes, Changes, rulers and the per-right Gantt timelines.

## 4. Repository & Docker layout
```
hist_map_dl1594/
  docker-compose.yml          # services: pipeline, web, e2e (copied)
  docker/pipeline.Dockerfile  # as hist_map
  docker/web.Dockerfile       # as hist_map
  Makefile                    # extract / parse / validate / curate / geocode / geometry / build-data / dev / test / e2e
  pdf/                        # source PDF (git-ignored)
  pipeline/denombrement/      # Python package
    text/                     # page text, page map, cleanup, index and old-forms tables, corrections
    parse/                    # NEW: numbered list and headings → entries; thematic lists
    extract/                  # LLM for holders, shares and prose sections (cut down from hist_map)
    data/                     # models, store, validate, schema
    curate/                   # entries → places, memberships, holdings; rules.yaml
    geo/                      # geocode, territories (copied, without years)
    web_data.py
  data/raw/                   # page text, tables (git-ignored)
  data/extracted/             # parser and LLM output (committed)
  data/curated/               # SOURCE OF TRUTH: entries.csv, places.csv, memberships.csv,
                              #   entities.csv, holdings.csv, features.csv, vocab.yaml,
                              #   rules.yaml, manual/*.csv, geocoding.csv
  data/geometry/              # cells.geojson, territories.geojson
  web/                        # Vite app; web/public/data/ holds the built JSON/GeoJSON
  doc/Plan.md
```
The Claude API key comes from `ANTHROPIC_API_KEY` in `.env` (git-ignored).

### What is copied from hist_map, and how
| hist_map | here |
|---|---|
| `docker/`, `docker-compose.yml`, `Makefile`, `.github/workflows/pages.yml` | copied; targets renamed, LLM targets kept |
| `pipeline/bailliage/text/` | `book.py`, `clean.py`, `pagemap.py` copied; Tesseract OCR and the letter-spacing repair dropped unless needed (the book has a text layer and no letter-spaced lines); `indexes.py` rewritten for this index's format |
| `pipeline/bailliage/extract/` | batch, cache and structured-output machinery copied; prompt and schema rewritten for holders and shares |
| `pipeline/bailliage/data/` | same pattern; models rewritten for §2; year checks removed |
| `pipeline/bailliage/curate/` | resolution and `rules.yaml` mechanism copied; merge rules for periods and events dropped |
| `pipeline/bailliage/geo/` | Wikidata, GeoNames and Japanese names copied; bounding box widened; `territories.py` without versions |
| `web/src/map`, `ui/`, `i18n.ts`, `model/colors.ts` | copied; year removed |
| `web/src/model/territories.ts` (`Hierarchy`, `territoryLevels`, the `h=feudal` switch) | copied; the hierarchy comes from the data (`h`, `rel`) instead of from the place type, and levels follow `admin` or `feudal` links only |
| `web/src/model/snapshot.ts`, the timeline, the Changes and Disputes views | dropped |
| `data/curated/geocoding.csv` | used as a seed for the bailliage d'Allemagne (~1,250 places), checked against this book's index |

## 5. Development stages

### Stage 0: Project setup
- Tasks:
  - `git init`, `.gitignore` (with `pdf/` in it before the first commit), README, LICENSE (MIT code, CC BY 4.0 data, as hist_map)
  - copy the Docker, Make and CI files from hist_map and rename the package to `denombrement`
  - an empty pipeline package and the Vite skeleton with the year removed
- Done when: `make dev` serves a blank map of Lorraine from the container, and `make test` runs pytest and vitest.
- **Status: done.**
  - Copied from hist_map: the licences (the data licence names Alix's text and the 1870 edition as public domain, and the scan as not part of the repository), `.dockerignore`, the web Dockerfile, `requirements.txt`, `pytest.ini`, `tsconfig.json`, `vite.config.ts`, `package.json` and its lock file (renamed), the Pages workflow (its data build step comes back in Stage 7) and `web/scripts/screenshot.mjs` (it waits for the map canvas).
  - `.gitignore` has `pdf/` and `*.pdf` from the first commit; `data/extracted/` is committed, unlike in hist_map.
  - Images are `hist-map-dl1594-pipeline` and `hist-map-dl1594-web`. The dev server runs on **port 5174**, so it can run next to hist_map's on 5173.
  - `pipeline/denombrement/`: `config.py` (paths, `YEAR = 1594`) and `python -m denombrement info` (`make info`), which finds the PDF.
  - `web/`: a blank MapLibre map with hist_map's base map (OpenFreeMap positron) and worker setup, centred on the duchy (`[6.5, 48.8]`, zoom 7.7). No year bar.
  - Tests: 3 pytest and 2 vitest pass; `tsc --noEmit` is clean. Checked by screenshot at 1280 px and 390 px, with no console errors.

### Stage 1: Text
- Tasks:
  - Read the text layer per page with PyMuPDF, keeping line positions.
  - Map PDF pages to printed pages (offset −11, roman numerals in the introduction, own numbering in the corrections) and check the mapping against the page headers.
  - Separate the editor's footnotes (they identify places and give variants) from the body text.
  - Clean up the frequent OCR confusions in this font: `cb`/`eb` → `ch`, `l`/`t` → `t` in "Sainct", `c`/`e`, `5`/`3`, `G`/`6`, `ïi`/`5`. Keep the raw text next to the cleaned text.
  - Cut the book into parts using Alix's table of contents (§1).
  - Parse the **table of place names** into `index.csv`: name, kind, commune, canton, département or state, entry numbers (expanding `1537, 38` and `709-715`), notes, and italics = unidentified (from the font flags).
  - Parse the **table of old forms** into `old_forms.csv`.
  - Parse the **corrections** into machine-applicable fixes where they are regular ("au lieu de 2210, lisez 2209"); list the rest for hand review.
- Done when: `data/raw/` has `pages.jsonl`, `parts/*.txt`, `index.csv`, `old_forms.csv` and `corrections.csv`, and a spot check of 10 pages and 50 index lines looks right.
- **Status: done.** Run `make extract` (about 30 s). Code is in `pipeline/denombrement/text/`: `book.py` (page ranges and part boundaries), `layout.py`, `pagemap.py`, `clean.py`, `indexes.py`, `corrections.py`, `ocr.py` and `extract.py`.
  - **Layout.** The scan is one column with an OCR text layer whose font sizes follow the glyph heights, so footnotes are told apart by size. They start at a small numbered line in the lower half of the page; everything below it is small, except that a note's short last line may be read larger. Spans that hold only a space are the word breaks and must be kept. The two-column table of old forms is split at the gutter; the column rule is sometimes read as a character (`|`, `{`, `!`) before a line, which is stripped.
  - **Page map.** The fixed offsets were right: printed = PDF + 1 (roman, PDF 4–13), PDF − 11 (PDF 14–275) and PDF − 275 (corrections, PDF 276–283). 212 headers agree, 29 are garbled, 33 pages have none, and the two that read like a neighbouring number are isolated misreadings (the nearest readable headers confirm the offset). The OCR often reads 3 as 5 and 1 as 4 in this font, in headers and entry numbers alike.
  - **Parts.** The book is cut at fixed boundaries (`book.PARTS`, a first PDF page and the part's first line) rather than from Alix's table of contents, which doesn't cover the editor's parts. 19 parts in `data/raw/parts/NN-<id>.txt` with `[p. N]` markers, and their footnotes in `NN-<id>-notes.txt`. The Dénombrement proper is 2,814 lines.
  - **Cleanup.** `fix_ocr` corrects only common words whose reading is certain (`el`/`cl` → `et`, `cbasleau` → `chasteau`, `Saincl` → `Sainct`, `dudiet` → `dudict`, `chaslellainie` → `chastellainie`, `Tordre` → `l'ordre`). Names are left to Stage 3. `pages.jsonl` keeps each line's raw text, cleaned text, position, size and part.
  - **Index:** 1,886 entries in `index.csv`. The italics are not in the text layer (all fonts are unembedded Times-Roman), so "unidentified" means no modern commune, canton, arrondissement or département is given. 113 entries are unidentified, mostly places located only by a historical unit ("prévôté de Sierck", "fief du bailliage d'Apremont"). Before splitting, the OCR variants of the index's words are normalized ("canlon", "coin," for "com.", ". canton" for ", canton"), and so are misreadings of a name's first letter ("llagécourt" → Hagécourt, "lmling" → Imling).
  - **Entry numbers.** 1,780 entries (94%) have clean numbers in range (1–2,487, the last entry being the Charterhouse of Rettel). A garbled number is read again by Tesseract from the line's image, but taken only where it agrees with every digit the text layer did read (42 entries; 14 more had nothing readable and take Tesseract's reading alone, marked `tesseract-only`). The 106 others stay flagged (`numbers_ok = 0`) for Stage 3, which can match them against the numbered sequence of the Dénombrement itself. Numbers past 2,487 are flagged too: they are digit misreadings ("2507" for 2307).
  - **Old forms:** 445 pairs in `old_forms.csv`; 10 rows where two entries ran together or the separator is lost are flagged `ok = 0`.
  - **Corrections:** 77 items in `corrections.csv`: 26 replace, 23 add, 12 delete, 7 renumber, 2 move, 3 notes and 4 others; 66 are machine-applicable. All but the last concern the two tables; the last is an observation on the introduction (the Bassigny).
  - Tests: 14 pytest tests in `tests/test_text.py` (cleanup, page labels, note starts, index entries and numbers, the second reading, old forms, corrections). Spot checks: 50 random index rows parse correctly, and on 10 random pages the extracted text matches pdftotext's character count.

### Stage 2: Schema & vocabularies
- Tasks:
  - Pydantic models and JSON Schema for §2.
  - `vocab.yaml`, starting from hist_map's and adding the territory types, tenures and orders.
  - A validator for: foreign keys; vocabulary membership; numbers unique and in sequence; every main-list entry has a district and a section; every territory has a hierarchy; `admin`, `feudal` and `ressort` links join the right hierarchies (§2); every settlement reaches the duchy; counterparts point at each other; no membership cycles.
- Done when: the validator passes on hand-written rows for the Nancy prévôté (entries 1–30), the fiefs of the office of Schaumburg and the abbey of Saint-Avold.
- **Status: done.** Code is in `pipeline/denombrement/data/` (`models.py`, `store.py`, `validate.py`, `schema.py`). `make validate` checks `data/curated/` (`--dir` for another directory, `--info` for information-level findings); `make schema` writes `data/schema/*.schema.json`, with the vocabulary keys as enums.
  - Tables: `entries`, `places`, `memberships`, `entities`, `holdings`, `features`; no table has years. `vocab.yaml` has labels in four languages for place types (also used as entry descriptors), territory types (each with its hierarchy), relations, counterpart bases, sections, tenures, series, religious orders, entity types, feature themes and confidence.
  - **Errors:**
    - foreign keys and vocabulary membership (list fields item by item)
    - missing labels or a missing territory hierarchy in the vocabulary
    - duplicate ids and entry numbers, and numbers outside 1–2487
    - a Dénombrement entry without its district or section
    - a district that isn't administrative, or a realm that isn't feudal
    - a territory whose hierarchy doesn't match its type
    - a holder on an administrative division
    - counterparts that don't point back, or are in the same hierarchy
    - `admin`/`feudal`/`ressort` links between the wrong kinds of territory
    - a settlement or division that doesn't reach the duchy
    - membership cycles
    - shares adding up to more than one
  - **Warnings:**
    - entries out of sequence
    - an entry's district or realm not mirrored by a membership
    - counterparts with different seats
    - a paired realm whose `ressort` isn't its counterpart
    - a realm that reaches nothing in the duchy
    - domain held by someone other than the duke
  - **Information:**
    - numbers missing from the sequence
    - realms without a holder
    - counterpart pairs whose member sets differ
  - The hand-checked sample is in `pipeline/tests/fixtures/sample/`: 51 entries, 60 places, 70 memberships, 4 entities and 55 holdings. It has 0 errors and 0 warnings; the three info findings are expected (Chaligny's holder isn't named there; the sample covers part of the numbering; the abbey's villages and the fief of Valmont are in the castellany but not in the duke's lordship).
    - The prévôté of Nancy: the domain (1–29), the first clergy entry (30), and the county of Chaligny answering to it.
    - The office of Schaumburg: domain, clergy ("Tholey, partie") and fiefs. Inside it, the prévôté of Keltern-Ostern, which is also a fief of the counts of Eberstein and Oberstein (a `heading` pair with two holders).
    - The castellanies and lordships of Hombourg and Saint-Avold (a `heading` pair outside the bailliages), with the abbey of Saint-Avold and its villages as a church temporality answering to the castellany.
  - The sample confirmed that index numbers need checking against names: Malgrange (3), Jarville (13) and Parey-Saint-Césaire (23) are indexed under 5, 15 and 25, and the corrections replace the index's identification of 1547 (Haupersweiler, not Urexweiler).
  - Tests: 26 more pytest tests in `tests/test_data.py` (the sample is valid; each check fires on a broken copy of it; the schema has the vocabulary enums). Stage 1 fix: an index range whose end equals its start ("75-75") no longer expands to a hundred numbers.

### Stage 3: Parsing the Dénombrement
- Tasks:
  - Split the main list into entries at `N. ` line starts, and join continuation lines.
  - **Repair the numbers** using the sequence: a number that breaks the order but fits after one digit fix (`577` between 376 and 379 → 377) is corrected; the index's numbers for the same name confirm it. Report gaps and duplicates.
  - Classify the lines between entries:
    - territory headings ("Prévosté et chastellainie de …", "Le ban de …, sçavoir", "Terre de Pierrefort"). Each one is split into its type words and its seat; the type words say which hierarchy it belongs to. A heading with words from both ("Prévosté, terre et seigneurie de Deneuvre") gives one administrative and one feudal territory. A feudal heading in a division's slot also gives both (§2, *Coinciding territories*).
    - `ressort` sentences ("pour l'esgard des fiedz … dépendent les terres …") and holder phrases ("tenuz en fief de Son Altesse par …")
    - section headings (*Domaine*, *Fiedvez*, *Clergé*, "Villages … qui sont des sauvegardes …")
    - footnotes
  - Keep two heading stacks, one per hierarchy, so each entry gets both its district and its realm. Check the administrative stack against Alix's table of contents.
  - Split each entry into its name and descriptors, and record "en partie" and "pour la moitié contre …".
  - Parse the thematic lists (entries ~2294–2447) with their headings: list type and religious order.
  - Send what the rules cannot settle to Claude: headings that name fief holders or shares, entries with long descriptions, the mines and chaumes pages and the Bitche village lists. Use the hist_map machinery: Batches API, structured output, a cache by request hash, and raw responses saved before parsing. Each request carries the matching index lines so names come back canonical.
- Done when: `data/extracted/entries.jsonl` has every number from 1 to the last, each entry has a district and a section, every heading has a hierarchy, and 50 random entries are checked against the scan.

### Stage 4: Identification & curation
- Tasks:
  - Join entries to the index by number. Each index line becomes a place, and each entry number it lists points to it. An entry that no index line claims gets a name match (old forms first, then a close spelling within its district), or is flagged.
  - Apply the corrections from Stage 1.
  - Create the territory places from the headings, keyed by hierarchy, type and seat (`prevote-dompaire`, `ban-sept`, `lordship-deneuvre`). Equivalent types are merged **within** a hierarchy only (prévôté et châtellenie = one division; terre et seigneurie = one realm), never across them. Pairs of coinciding territories are created from the four sources in §2 (`heading`, `slot`, `alix_list`, `rule`), linked by `counterpart_id` and given their members.
  - Generate `admin`, `feudal` and `ressort` memberships, and the holders of feudal realms (the duke where the realm is domain).
  - Generate `memberships`, `holdings` and `entities`.
  - Write the review report: entries without a place, places claimed by entries in distant districts, settlements with no district, realms with no `ressort` or no holder, names the index leaves unidentified, holders not resolved, numbers repaired.
  - Hand fixes go in `manual/` and `rules.yaml`, never into generated tables, so `make curate` can always be re-run.
- Done when: the validator is green, at least 95% of main-list entries have a place, and the report is worked through.

### Stage 5: Geocoding & names
- Tasks:
  - Copy hist_map's geocoder. Widen the bounding box to about 5.3–7.7°E, 47.8–49.9°N (Lorraine, the Vosges, the Saarland, the Palatinate and Alsace edges).
  - Match with the index's commune and canton. These are the 1870 communes and cantons: Meurthe, Moselle, Vosges, Meuse, Bas-Rhin, Haut-Rhin, the Prussian Rhine Province (Pr.), the Bavarian Palatinate (Bav.), Luxembourg, Birkenfeld. Many have since merged, so former-commune Wikidata items are allowed as targets, and the canton ranks candidates by distance.
  - Seed from hist_map's `geocoding.csv` where the index agrees.
  - Hamlets and lost places are placed at their commune and marked approximate, as in hist_map.
  - Names: the French name is the modern one from the index; German and English come from Wikidata, and Japanese from the hist_map method.
- Done when: at least 95% of identified places have coordinates, and the rest are listed in the report.

### Stage 6: Territory geometry
- Tasks:
  - Voronoi cells from all located settlements, as in hist_map, plus **neutral seed points** for communes in the bounding box that the book does not list (from Wikidata). Without them, the cells of Lorraine villages would cover the bishoprics' enclaves and the Barrois.
  - Dissolve cells per hierarchy: administrative divisions at each level (they tile the duchy), then feudal realms from their own members only (they leave gaps). There is one version per territory, with no years.
  - Split places (two divisions, "en partie") give their cell to the first division and are hatched in the others.
  - Approximate and far-away places add no land, as in hist_map.
  - Later: the Bitche boundary walk as a line, and the rivers.
- Done when: the bailliage and prévôté areas render without gaps, the feudal realms render inside them, and the enclaves of Metz and Toul show as holes.

### Stage 7: Data build
- Tasks: compile the curated data into `web/public/data/`:
  - `meta.json`: source, version, counts, vocabularies
  - `places.json`: `{id, kind, type, name:{fr,de,en,ja}, variants[], index:{kind, commune, canton, dept}, lat, lon, geo, approx, wd, parents:[{id, rel, share}], tenure, entries[], pages}`; territories also have `h` (`admin`/`feudal`), `holder` and `counterpart`
  - `entries.json`: `{no, text, name, desc[], district, realm, section, holders[], share, with[], list, order, place, page}`
  - `entities.json`: `{id, type, name:{en,fr,de,ja}, rank, holdings}`
  - `features.json`, `cells.geojson`, and `territories.geojson` with features `{id, h, level, place_type, settlements}`

  It refuses to build while there are validation errors.
- Done when: the build is deterministic (a rebuild is byte-identical) and the data stays under about 2 MB.

### Stage 8: Frontend core
- Tasks:
  - Copy hist_map's app and remove the year: the year bar, `snapshot.ts`, the year in the URL and the year in the territory model.
  - URL state: `#/map?color=tenure&lang=fr&place=saint-avold`.
  - Map: cells and points coloured by tenure, holder, district or realm; hatching for shares; the hover tooltip.
  - Place panel with the entries, the index identification and the two chains (district and realm).
  - Copy the i18n with the new vocabulary.
- Done when: the map shows the whole duchy coloured by tenure, and clicking a place shows its entries with their numbers and pages.

### Stage 9: Screens
Implement the remaining screens from §3 in this order: Territories, Table, Holders, Church & resources, About.
- Done when: every screen works in all four languages at 1280 px and on a phone, with no console errors.

### Stage 10: QA & polish
- Tasks:
  - Port hist_map's Playwright suites (`core`, `views`, `layout`, `a11y`, `perf`) without the year tests.
  - Add tests for: the place panel listing several entries; a split place; the territory levels; table filters and CSV export.
- Done when: `make e2e` passes, and axe reports no serious or critical violations.

### Stage 11: Deployment
- Tasks: the GitHub Pages workflow from hist_map: tests, `build-data` from the committed `data/curated/` and `data/geometry/`, then the Vite build under `/<repository name>/`.

## 6. Risks & open points
- **OCR numbers:** a misread number attaches an entry to the wrong place. The sequence check and the index's numbers catch most of them; the rest show up as places in implausible districts.
- **The index can be wrong.** The editor corrected it in the corrections pages, and some identifications are only "peut-être". Corrections are applied, and doubtful identifications are kept at medium or low confidence.
- **1870 communes and cantons** do not match modern ones: there are the 1871 border, the merging of Meurthe and Moselle, and many commune mergers.
- **Homonyms:** many villages share names (Neunkirchen, Hombourg, Fontenoy). The index's canton and the district's neighbours decide.
- **Lost villages and hamlets** are placed approximately and add no land.
- **Gaps on the map:** the Barrois, the Three Bishoprics and the neighbouring Empire lands are not in the book. The map must make clear that these blanks mean "not Lorraine in the Dénombrement", not "unknown".
- **Coinciding territories the book doesn't name.** A *châtellenie* or an *office* was often a former lordship of the duke, but the heading may give only the administrative word. Those pairs come only from `rules.yaml`, each with a source. The report lists candidates for review: offices and châtellenies whose seat is a castle, and land the introduction says the duke acquired (Bitche, Phalsbourg, Hombourg, Saint-Avold, Blâmont). They are not guessed in code.
- **Holders are often implicit.** A *Fiedvez* section usually does not name the vassal. Those holdings stay "fief, holder not named" rather than guessed.
- **The thematic lists repeat places** with different spellings. They are joined through the index like the main list.
- **Voronoi areas are approximations,** and the UI says so.

## 7. Verification (per stage)
- `make test`: pytest runs the number repair, the heading classification, the index parser (abbreviated numbers and ranges) and the validator; vitest runs the colour and territory logic.
- `make validate`: checks integrity and prints coverage (entries with a place, places located, low-confidence count).
- Manual checks against the book:
  - Entry 1 is Nancy, the ducal residence, in the domain of the prévôté of Nancy.
  - Commercy is held half by the duke and half by the counts of La Roche.
  - The villages of the chapter of Toul under the prévôté of Gondreville are ducal safeguards.
  - Entry 2240 is Saint-Avold "ou Saint-Nabor", and entries 2268–2280 are the villages of its abbey.
  - The prévôté of Sierck has four parts: the prévôté, the sous-prévôté, the Landschultheisserei and the prévôté of Condé.
  - The Dénombrement lists Marsal although it only became Lorraine in 1594–95.
  - Bitche, Hombourg, Saint-Avold, Phalsbourg and Sarrebourg are outside the bailliages.
  - "Prévosté, terre et seigneurie de Deneuvre" gives the prévôté of Deneuvre (administrative) and the lordship of Deneuvre (feudal, held by the duke), with the same members.
  - The terre and seigneurie of Faulquemont, directly under the bailliage d'Allemagne, is recorded both as a lordship and as a division of that bailliage (`slot`).
  - The county of Blâmont is recorded both as a county held by the duke and as a division directly under the duchy (`slot`, `alix_list`).
  - The county of Chaligny and the terres of L'Avant-Garde, Le Châtelet, Pierrefort and Hey are feudal realms whose `ressort` is the prévôté of Nancy.
  - The bans of Sept, Taintrux and Sardey are administrative divisions of the prévôté of Saint-Dié.
  - The prévôté of "Keltern-Ostern" (entries 1546–1566, castellany of Schaumburg) is a fief of the counts of Eberstein and Oberstein.
- `make e2e`: Playwright in a container against `make dev`.
