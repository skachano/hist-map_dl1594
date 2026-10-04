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
The same columns as hist_map's `places.csv`: `id`, `kind` (`settlement` / `territory`), `name_fr/de/en`, `variants[]` (the book's spellings: the lists' entries), `old_forms[]` (the edition's table of old forms), `place_type`, `lat`, `lon`, `wikidata_id`, `geonames_id`, `modern_country`, `source_page`, `confidence`, `notes`. Columns added:
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
`child_id`, `parent_id`, `relation`, `share` (`part` when the book says "en partie"), `source_page`, `confidence`, `notes`. There are no years. A place may have several parents, as in hist_map: one row per territory it belongs to. Besides the lists' headings, rows come from `manual/memberships.csv` (with their page and why) and from the shared lands of a division and its realm. `relation` is one of:
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

### `index_links`: the index's numbers, resolved
One row per number the editor's index prints, resolved to the entry it means: `place_id`, `entry_no`, `index_name` (the index line's heading), `printed` (the number as read, when it differs), `status` (`agrees`, `spelling differs`, `corrected`, `manual`), `source_page` (the index page), `confidence`, `notes`. An entry that names several places ("Volfflingen et Weissweiller") has a link to each; the place it is matched to stays `entries.place_id`.

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

1. **Tenures** (the default and first tab, named Map, until after Stage 10; now second, after Territories): settlement cells and points, coloured by tenure. Originally there were these modes:
   - **tenure**: domain / fief / clergy, with safeguard and other tenures in grey (three validated CVD-safe colours plus grey, as in hist_map)
   - **holder**: the legend picks which holders get the three colours, as in hist_map

   The **district** and **realm** modes were dropped after Stage 10: the Territories view shows the same divisions and realms, at every level, with clickable areas. The **holder** mode was dropped after that: the Holders view maps one holder's places. With tenure the only colouring, the tab was renamed Tenures.

   Hatching marks shared places ("en partie", "pour la moitié"). Places outside the duchy that the book doesn't list (the Three Bishoprics, the Barrois) are left blank and labelled.
2. **Territories** (the default view and first tab since after Stage 10): hist_map's Territories view without the year, with a switch between the two hierarchies (`#/territories?h=admin|feudal&lvl=…`):
   - **Administrative divisions:** level 1 = bailliages and the towns outside them; level 2 = prévôtés, châtellenies, offices; level 3 = bans, mairies, vals; 0 = all levels. Areas tile the duchy.
   - **Feudal realms:** level 1 = realms held directly (counties, terres, lordships, church temporalities); level 2 = realms inside them; 0 = all. Areas cover only the realms' members, so the land between them is blank.
   - Both hierarchies are coloured by kind of realm, as in hist_map (see "the Territories screen as in hist_map" below), and a "Kind of realm" menu shows one kind at every level.

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
- **Status: rule-based parse done; the Claude pass is not run.** `make parse` (a few seconds) writes `data/extracted/`: `entries.jsonl`, `territories.jsonl`, `features.jsonl` (chaumes), `prose.jsonl` (the sentences that aren't headings) and `parse_report.md` (the review list). Code is in `pipeline/denombrement/parse/`: `numbering.py`, `structure.py`, `headings.yaml`, `features.py` and `report.py`.
  - **Numbers.** A line-start token is scored against each candidate number by an alignment cost in which the scan's usual misreadings are cheap (3/5, 1/4, letters and symbols for digits). A beam search then picks the increasing numbering with the least total cost over the whole list; greedy reading drifted after one wrong pick. A second pass looks for numbers still missing between two numbered neighbours, also inside a line where the OCR ran two entries together ("Sainct-Remvmonl.1156. Allainville."), and splits it.
    - 2,485 of 2,487 numbers are found: 1,968 read exactly, 387 through a usual confusion, 130 from a garbled token or a less usual misreading (listed in the report).
    - 86 is not in the book's text or the index, and 1513 is lost in a garbled line ("î ».1514. outzweillcr.Kxweiller."). (After Stage 10, `rules.yaml entry_splits` restores it from the printed page: 1513 Exweiller, 1514 Sutzweiller.)
  - **Headings.** Blocks are entries, section headings (OCR-tolerant: "Fiedvcz", "Doroaine", "Nancy pour le clergé"), territory headings or prose. A territory heading is told by its type words, with its seat taken from the words after them. A line ending with a comma is a list item, unless an entry follows it ("La terre de L'avantgarde,"). A sentence with a verb is prose. `headings.yaml` settles 45 headings the words don't: bare names ("Le Sargaw.", "Raon."), the four parts of the prévôté of Sierck, Keltern-Ostern, Blâmont, Deneuvre, the lands outside the bailliages, and group labels such as "Bassigny." and "Trèverois.".
  - **Two stacks.** The administrative stack is bailliage → prévôté/office/castellany → ban/mairie/val. The open realm is kept beside it. A realm heading inside a district ("Terre de Pierrefort") answers to the district at level 2 (`ressort`), and its entries keep that district. A terre the bailliage's opening sentence lists among its prévôtés is a slot pair: Puttelange, Beaurains, Morhange, Faulquemont and Forbach in the bailliage d'Allemagne. The terres the prévôté of Nancy's sentence says "dépendent" of it are realms answering to it: Chaligny, L'Avant-Garde, Le Châtelet, Pierrefort, Hey and Commercy. Outside the bailliages, towns, vals and terres stand directly under the duchy.
    - Result: 134 territories (107 divisions, 27 realms, 15 pairs).
    - Seats get their modern names from the old-forms table and the index. Matching is exact first, then with the scan's c/e and l/t confusions made equal, then fuzzy (same first letter). Index names come before old forms in the near matches, because the old-forms table maps some spellings to other places ("Einville. Euville."). Index names are OCR'd too ("Einvillc"); Stage 4 fixes the spellings.
  - **Entries:** 2,288 in the Dénombrement (767 domain, 449 clergy, 854 fief and 218 `other`) and 197 in the thematic lists (towns, cathedrals, collegiate churches, abbeys of monks and of nuns, Grey Sisters and other sisters under "Couventz de religieuses", priories, friaries, other convents, commanderies). Each has its name, descriptors, religious order and share ("partie" → `part`, "pour la moitié" → `1/2`, with the wording kept).
    - The 218 `other` entries are listed before any section heading, where the book gives none: the lands of Hombourg and Saint-Avold, Beaurains, Puttelange and the other terres; the glassworks of Darney; the Saargau; Bitche's granges. Stage 4 decides them from the realm's holder.
  - **Chaumes:** 23, with their other names, gîtes and prévôté. The mines table (pp. 116–117) can't be rebuilt from the text layer.
  - **Checks:**
    - Alix's table of contents: 60 of its 62 lines have a matching heading. The other two are worded differently: "Darney ; les verrières" and Sultzbach, which the text spells "Sulrzbach.".
    - 50 random entries against the scan: 48 were right at first. The two errors were systematic and are fixed: a seat mapped through the old-forms table to the wrong place, and a clergy section "pour … Sainct-Diey et Raon" that covers the whole prévôté.
  - Tests: 12 pytest tests in `tests/test_parse.py` (number costs and the alignment, finding numbers inside lines, sections, heading types and seats, overrides, entry details, the gazetteer, a parsed passage, chaumes).
  - **Not done: the Claude pass.** What the rules leave is small, and its wording is kept in `parse_report.md`:
    - the holders of one heading (Keltern-Ostern) and 40 shares
    - five sentences on sovereignty and justice (the Saargau, Merzig, Commercy)
    - the mines table
    - the Bitche description (pp. 134–171)

    Resolving holders and shares to entities can be done by hand in Stage 4 (`rules.yaml`) or by Claude; the mines need the page image.

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
- **Status: done, with review items left.** `make curate` (about 30 s) writes `data/curated/*.csv` and `data/review/report.md` from `data/extracted/`, `data/raw/index.csv` and `old_forms.csv`, `rules.yaml` and `manual/entities.csv`. Code is in `pipeline/denombrement/curate/` (`build.py`, `corrections.py`). The validator is green: 0 errors, 0 warnings, 50 information notes.
  - **Matching.** An entry is matched to an index line by number and name together, because the index's numbers are misread like the list's (Malgrange, entry 3, is indexed under 5).
    - Names are compared without articles, with "Sainct" = "Saint", the scan's c/e and l/t confusions made equal, and against the first part of compound modern names ("Charmes" = "Charmes-sur-Moselle"). The table of old forms bridges spellings that look nothing alike ("Marchainville" → Maxéville).
    - Order of preference:
      1. the line with the entry's number, when the name fits (≥ 0.5)
      2. a line whose number differs by one confused digit, when its name fits clearly better (≥ 0.75, and 0.3 better)
      3. the only line with the number, when the old and new names still share something (≥ 0.25)
      4. a line with a confused number (≥ 0.8)
      5. a line whose number reads loosely as this one, or whose numbers are garbled (≥ 0.82)
      6. the name alone (≥ 0.9)
    - A strong name match beats a weak number match: Sarrebourg's index line lost its numbers to the OCR.
    - A thematic-list entry with a weak match takes the place of the Dénombrement entry with the same name.
    - Thresholds were raised until wrong matches stopped showing up in the review: a missing match is reported, a wrong one isn't.
  - **Result:** 2,174 of 2,288 Dénombrement entries (95.0%) match an index line.
    - By match kind: 1,918 by number and name, 240 by a confused number, 77 by number only, 88 by a loose number, 20 by name, 6 by rule.
    - 127 entries (including list entries) aren't in the index and get a place of their own, flagged `low` confidence.
    - 1,916 settlements: 1,498 villages, 270 hamlets, 38 farmsteads, 31 towns, 20 bourgs… 98 are `lost` (the index gives no modern commune).
  - **Corrections:** 52 of the 66 machine-applicable corrections apply. The page numbers they cite are misread too (3 for 5: "p. 258" for 238), so nearby pages and those variants are searched. The 14 left change spellings inside other lines or name lines the OCR garbled. The report lists them, with the 11 corrections that need reading.
  - **Territories:** 135 (107 divisions, 28 realms, 15 pairs). Their ids use the type key with hyphens (`town-district-marsal`) and `temporality-abbey-<seat>` for church lands. The parse also opens an abbey's lands from an entry ("L'abbaye dudict Sainct-Avol, … de laquelle dépendent les villages cy-après") and closes them at the next section.
  - **Holdings:** 2,031 (774 domain, 832 fief, 425 clergy). Domain and safeguards are the duke's; fiefs and clergy take their realm's holder when the book gives one. Entries listed without a section heading under a realm of the duke count as domain, under a realm with another holder as fief; 168 stay `other` where the realm's holder is unknown.
  - **`rules.yaml` (worked through):**
    - modern names for 61 garbled territory seats
    - realm holders the book gives (Keltern-Ostern: Eberstein and Oberstein; Vaudémont, Blâmont, Deneuvre, Bitche, Phalsbourg, Hombourg and Saint-Avold: the duke), each with its source
    - names for two descriptive entries (2176 Lothringen, 2177 Altheim)
    - four index lines and two new places for entries the numbers misled (Chamoysy = Chaumousey, Lebeufville, Sault = Saulx-en-Woëvre, Gunweiller = Guenviller; Nittel, Gersweiler)
  - **Checks:**
    - The 51 hand-checked entries of the Stage 2 sample all get the same place and section (`tests/test_curate.py`). The only difference is the index's OCR spelling of the names ("Tholcy").
    - Places in more than one bailliage: 45. Most are genuine (fiefs are listed under the prévôté they owe homage to, and some villages are split: "Dommart-aux-Bois pour le tiers et les deux tiers à Chastel"). The six that were wrong matches are fixed in `rules.yaml`.
  - **Left for later:**
    - Place names are the index's spellings, OCR'd ("Picrrevillc"); Stage 5 replaces them with Wikidata's.
    - `modern_country` is provisional (the index gives the state on few lines); Stage 5 sets it from the coordinates.
    - 20 realms have no holder, because the book doesn't name one: Morhange, Forbach, Puttelange, Beaurains, Faulquemont, Chaligny, Commercy, Sarralbe…
    - The 40 shares keep their wording but have no `share_with` holders yet.
  - Tests: 7 more pytest tests in `tests/test_curate.py` (names, similarity, number variants, the matcher, correction pages, agreement with the sample). 58 in all.

### Stage 5: Geocoding & names
- Tasks:
  - Copy hist_map's geocoder. Widen the bounding box to about 5.3–7.7°E, 47.8–49.9°N (Lorraine, the Vosges, the Saarland, the Palatinate and Alsace edges).
  - Match with the index's commune and canton. These are the 1870 communes and cantons: Meurthe, Moselle, Vosges, Meuse, Bas-Rhin, Haut-Rhin, the Prussian Rhine Province (Pr.), the Bavarian Palatinate (Bav.), Luxembourg, Birkenfeld. Many have since merged, so former-commune Wikidata items are allowed as targets, and the canton ranks candidates by distance.
  - Seed from hist_map's `geocoding.csv` where the index agrees.
  - Hamlets and lost places are placed at their commune and marked approximate, as in hist_map.
  - Names: the French name is the modern one from the index; German and English come from Wikidata, and Japanese from the hist_map method.
- Done when: at least 95% of identified places have coordinates, and the rest are listed in the report.
- **Status: done.** `make geocode` (about 3 minutes; the downloads are cached in `data/raw/geo_cache/`) writes `data/curated/geocoding.csv`. `make curate` merges it into `places.csv` and `names_ja.csv` and adds "Geocoding to check" to the review report. `make data` runs parse, curate, geocode and curate. Code is in `pipeline/denombrement/geo/` (`wikidata.py`, `geonames.py`, `geocode.py`).
  - **Different from hist_map: a regional download.** The places' names are the index's OCR spellings ("Picrrevillc", "Tholcy"), so exact-label queries would miss most of them. Instead, every settlement Wikidata has in the box 5.3–7.8°E, 47.8–50.0°N is downloaded once, in 0.5° tiles: 7,689 items (communes, former communes, German municipalities and Ortsteile, villages, hamlets, castles and abbeys, with fr/de/en/ja labels). Add the GeoNames dumps (7,668 entries) and hist_map's hand-checked geocoding of the bailliage d'Allemagne (948 places, copied into the cache), and the matching is local.
  - **Keys:** Stage 4's loose name key, with this font's b/h confusion made equal too ("Robrbacb" = Rohrbach). Database labels are also indexed by the base of compound names ("Sierck-les-Bains" → Sierck). Canton and commune names lose OCR junk first ("île Gorze", "Fresnes-en-Voèvre(Meuse;, 1891").
  - **Anchors and matching:**
    1. A place's anchor is the commune the index gives (hamlets), else the canton's chef-lieu, found near the canton.
    2. Candidates within 12 km of a commune or 25 km of a canton are scored by name similarity (≥ 0.84), class (settlements first) and distance.
    3. A hamlet the databases lack is placed at its commune (`approximate`).
    4. Without an anchor, an exact name that points to one spot in the region is taken.
  - **Second pass:** the median of the reliable located members of the place's districts (not bailliages, which are too large).
    - Places with no anchor, an ambiguous match, or more than 35 km away are matched again within 30 km of it. Short names (under 7 letters) must match almost exactly there, so "Viller" goes to Villers-lès-Nancy, not Ville-en-Vermois.
    - A hamlet placed far away is moved to its commune's namesake near the district (Rupt-sur-Moselle, not Rupt-en-Woëvre).
    - A match on the index's own canton or commune keeps its confidence even when it is far from its district (fiefs owe homage to distant prévôtés: Coussey, Celles-sur-Plaine); anything else that far becomes `low`.
  - **One place per Wikidata item** (added in Stage 7, when two places turned out to share items).
    - When two places are matched to one item, the one whose name fits it best keeps it; the other looks again with that item excluded, or stays unlocated.
    - A village's own name is compared without the b/h folding (Hénaménil is not Bénaménil), and only the anchors use it.
    - A match on the base of a compound name counts 0.9 (Sexey-lès-Bois is not Sexey-aux-Forges), and one on the book's old spelling 0.95 rather than the index's name. Entry 1516 is spelt "Budingen", Buding's German name, but the index says Budange.
    - The name weighs most in the score, so an exact hamlet beats a neighbouring commune of a near name.
    - Two index lines for the same village (same canton, near-identical names) keep the item, and `make curate` merges them into one place.
  - Ties are broken in a fixed order: two runs give byte-identical files.
  - **Result:** 1,661 of 1,916 settlements located (86.7%). Of the places the index identifies, 1,610 of 1,685 (95.5%).
    - By method: Wikidata 886 (624 high), hist_map 414, GeoNames 171, approximate (at their commune) 190.
    - 255 unlocated: mostly entries the index doesn't identify and places it calls lost, plus 75 identified places with heavily OCR'd names or whose only match belonged to another place, listed in the report.
    - 66 matches are `low` confidence and listed for review.
    - A map of the located settlements by bailliage (`data/review/geocoding.png`) shows each bailliage as a coherent area.
  - **Names:** a settlement located with medium or high confidence takes Wikidata's French name ("Tholey" for the index's "Tholcy"), and the index's spelling joins the book's spellings as variants. German and English come from Wikidata. Its id is re-keyed from the modern name (`tholey`) where no namesake has it; all references follow. `modern_country` comes from Wikidata or GeoNames.
    - Territories get a label point at their seat (a member settlement of the seat's name), else the centre of their located members: 134 of 135.
    - Japanese: Wikidata's label for settlements (few villages have one), the seat's Japanese name plus the type for territories ("ナンシー代官区"), and `manual/names_ja.csv` wins: 103 names. The app falls back to French.
  - Hand decisions go in the `geocode` section of `rules.yaml`: `{wikidata: Q…}`, `{lat, lon}`, `{approximate: place}` or `{unlocated: true}`, with a note. None were needed to reach the target.
  - Tests: 6 pytest tests in `tests/test_geo.py` (keys, names, the namesake nearest to the anchor, OCR tolerance, b and h kept apart in village names, distance).

### Stage 6: Territory geometry
- Tasks:
  - (Changed after Stage 10: neutral points only in the known foreign lands; see below.) Voronoi cells from all located settlements, as in hist_map, plus **neutral seed points** for communes in the bounding box that the book does not list (from Wikidata). Without them, the cells of Lorraine villages would cover the bishoprics' enclaves and the Barrois.
  - Dissolve cells per hierarchy: administrative divisions at each level (they tile the duchy), then feudal realms from their own members only (they leave gaps). There is one version per territory, with no years.
  - Split places (two divisions, "en partie") are in both areas, as in hist_map (changed after Stage 10; it was the first division only).
  - Approximate and far-away places add no land, as in hist_map.
  - Later: the Bitche boundary walk as a line, and the rivers.
- Done when: the bailliage and prévôté areas render without gaps, the feudal realms render inside them, and the enclaves of Metz and Toul show as holes.
- **Status: done.** `make geometry` (a few seconds) writes `data/geometry/cells.geojson` (1,382 settlement cells, 0.3 MB) and `territories.geojson` (131 areas, 0.2 MB), plus previews in `data/review/areas-bailliages.png` and `areas-realms.png`. Code is in `pipeline/denombrement/geo/territories.py`.
  - **Cells.** Each located settlement point gets a Voronoi cell in EPSG:3035, clipped to 6 km around the settlements. Places at one point (a hamlet placed at its commune) share its cell.
  - **Neutral seeds.** The Wikidata communes of the region that the book doesn't list take cells of their own and belong to no territory: 2,944 of them. A commune isn't neutral when it is one of our places' Wikidata items, lies within 1.5 km of a listed settlement, or bears the name of one of the book's places (unlocated ones included) or of a commune the index gives for a hamlet. Without that last test, the book's own unlocated villages made holes inside Lorraine.
  - **Areas.** A division's area is the union of the cells of the settlements it reaches through `admin` links, a realm's through `feudal` links. A settlement in two divisions is in both, as in hist_map: its cell is in both areas, which overlap there, and both list it in `shared`. (Until the change after Stage 10, it gave its cell to the first division in the book's order.)
  - **No land** comes from places placed at their commune, matched with low confidence, or flagged far from their district. They stay members and keep their points.
  - Feature properties are `{id, hierarchy, place_type, level, settlements, shared[]}`, with one version per territory and no years.
  - **Checks:**
    - Metz, Toul and Verdun lie in no area: the enclaves of the Three Bishoprics are holes.
    - The bailliages tile the duchy at about 13,000 km² in all, the bailliage d'Allemagne in the north-east, Vosges in the south, Nancy in the centre with the prévôté of Saint-Dié to the east.
    - The realms render inside them (Vaudémont, Blâmont, Bitche, Keltern-Ostern around Oberkirchen, Morhange, Faulquemont, Commercy west of Toul).
    - Two runs give identical files.
  - **Known gaps:**
    - Nancy (36 pieces) and Apremont (37) are fragmented. Most pieces are fiefs listed under a prévôté they owe homage to while lying elsewhere, and Apremont was interleaved with the Barrois.
    - Small holes remain where the book's villages are unlocated.
    - 4 territories have no located members: the bans of Grandvillers et Dompierre, Maizey and Vaudicourt, and the mairie of Steinbach.
  - Tests: 3 pytest tests in `tests/test_territories.py` (which places add no land, a neutral seed makes a hole, cells are clipped). 66 in all.

### Stage 7: Data build
- Tasks: compile the curated data into `web/public/data/`:
  - `meta.json`: source, version, counts, vocabularies
  - `places.json`: `{id, kind, type, name:{fr,de,en,ja}, variants[], index:{kind, commune, canton, dept}, lat, lon, geo, approx, wd, parents:[{id, rel, share}], tenure, entries[], pages}`; territories also have `h` (`admin`/`feudal`), `holder` and `counterpart`
  - `entries.json`: `{no, text, name, desc[], district, realm, section, holders[], share, with[], list, order, place, page}`
  - `entities.json`: `{id, type, name:{en,fr,de,ja}, rank, holdings}`
  - `features.json`, `cells.geojson`, and `territories.geojson` with features `{id, h, level, place_type, settlements}`

  It refuses to build while there are validation errors.
- Done when: the build is deterministic (a rebuild is byte-identical) and the data stays under about 2 MB.
- **Status: done.** `make build-data` writes `web/public/data/` (git-ignored; `make dev` builds it when missing) and refuses to run while the curated data has validation errors. `make data` runs the whole chain: parse, curate, geocode, curate, geometry, build-data. Code is in `pipeline/denombrement/web_data.py`. The GitHub Pages workflow builds the data again from the committed `data/curated/` and `data/geometry/`.
  - **Size and determinism:** 1.76 MB in all (places 821 kB, entries 378 kB, cells 328 kB, territories 222 kB, meta 11 kB), within the 2 MB budget. A rebuild is byte-identical. Empty fields are omitted; zeros are kept.
  - **File formats** (keys as the app sees them):
    - `meta.json`: `year`, `source`, `version` (a hash of the data files), `counts`, and every vocabulary with its en/fr/de/ja labels (`territory_types` with their `hierarchy`).
    - `places.json`: `{id, kind, type, name:{fr,de,en,ja}, variants[], index:{kind, commune, canton, dept}, lat, lon, geo, approx, lost, wd, country, h, holder[], counterpart, basis, parents:[{id, rel, share}], tenure, hold:[{t, h, share, with[], e[]}], entries[], pages, conf}`. `tenure` is the place's main tenure (domain, else fief, else clergy, else safeguard); `hold` lists every holding with its entries.
    - `entries.json`: in the book's order, `{no, text, name, desc[], district, realm, section, holders[], share, with[], series, order, place, page, conf}`. `series` is absent for the Dénombrement itself. The text is the full entry: the book is in the public domain.
    - `entities.json`: `{id, type, name:{en,fr,de,ja}, rank, holdings}`.
    - `features.json`: the chaumes, `{id, theme, name, place, attrs:{gistes, provostship, also[]}, page}`.
    - `territories.geojson`: `{id, hierarchy, place_type, level, settlements, shared[]}`. `cells.geojson`: `{id, also[]}`.
  - Fixes this stage needed:
    - Two places could share a Wikidata item (47 cases). The geocoder now gives an item to one place, and curate merges genuine duplicates (see Stage 5).
    - A place's own name no longer appears among its variants.
  - Tests: 3 pytest tests in `tests/test_web_data.py` (compact output keeps zeros, feature attributes, the built files: order, links, counterparts). 70 in all.

### Stage 8: Frontend core
- Tasks:
  - Copy hist_map's app and remove the year: the year bar, `snapshot.ts`, the year in the URL and the year in the territory model.
  - URL state: `#/map?color=tenure&lang=fr&place=saint-avold`.
  - Map: cells and points coloured by tenure, holder, district or realm; hatching for shares; the hover tooltip.
  - Place panel with the entries, the index identification and the two chains (district and realm).
  - Copy the i18n with the new vocabulary.
- Done when: the map shows the whole duchy coloured by tenure, and clicking a place shows its entries with their numbers and pages.
- **Status: done.** Vanilla TypeScript with MapLibre in `web/src/`, adapted from hist_map without the year:
  - **Data:** `data/types.ts` and `load.ts` for the Stage 7 files (cache-busted by the data version); entries are indexed by number.
  - **State:** `state/store.ts`, with the state mirrored in the URL: `#/map?color=tenure|holder|district|realm&lang=fr&place=saint-avold&c=…`. No year, no right types.
  - **Model:** `model/places.ts` gives each place's chains up each hierarchy (one per parent, so a village "en partie" in two prévôtés has two), the division a realm answers to, the main holding (domain first, then fief, clergy, safeguard), whether it is held in part, the kind of realm it lies in, its style per mode and the legend counts. `model/colors.ts` holds the colours.
  - **Map:** `map/mapView.ts`, `icons.ts`.
    - Cells and points coloured per mode through feature state; places at one point share their cell, and the place that owns it colours it.
    - Hatching for places held in part or jointly; points placed at their commune are hollow.
    - The duchy's outline, thin and grey; the map fits it on load.
    - In the districts mode, the bailliages and the lands outside them as grey areas with white borders and labels.
  - **Header** (`ui/controls.ts`): the title, the four colour modes as tabs, the language switch. No year bar.
  - **Legend** (`ui/legend.ts`) for each mode:
    - tenure: domain, fief, church lands, safeguard, not stated, with counts
    - holder: the three coloured holders, "holder not named" and the picker for other holders
    - realm: counties, lordships/terres/fiefs, church lands, in no named realm
    - district: the 21 top divisions, as links
    - always the hatching key, the kinds of place, and notes that areas are approximate and that blank land is not Lorraine in the Dénombrement
  - **Place panel** (`ui/panel.ts`):
    - names in four languages and the book's spellings
    - type in four languages
    - the editor's identification (kind, commune, canton, département), or "not identified"
    - District and Realm chains, clickable from the top down
    - for territories: what they answer to, their counterpart on the same land with its basis, their holders, and their member territories and places
    - the location's reliability (approximate, uncertain, not located)
    - every holding with its tenure, holder ("not named" for fiefs and church lands without one), share and entry numbers
    - every entry naming the place: number, the text in « », section or list, district, realm and page
    - the source line
  - **Tooltip:** name, kind of place, tenure and holder (tenure and holder modes), and the district chain, or the realm chain in the realm mode.
  - **i18n:** the interface strings in EN/FR/DE/JA. Vocabulary labels come from `meta.json`; names fall back through French.
  - Checked by screenshot, with no console errors:
    - tenure in English and German at 1280 px
    - districts in French with Saint-Avold selected (entries 2240 and 2267 with pages 114–115, district and realm chains)
    - realms with Guessling (the abbey of Saint-Avold's lands)
    - Japanese on a phone (390 px: map above, panel below)
  - Tests: 13 vitest tests (config, URL state, place chains, tenure order, sharing, kinds of realm, styles per mode, tooltip position).
  - Carried to Stage 9: the Territories, Holders, Table, Church & resources and About views. The view tabs appear once there is more than one view.

### Stage 9: Screens
Implement the remaining screens from §3 in this order: Territories, Table, Holders, Church & resources, About.
- Done when: every screen works in all four languages at 1280 px and on a phone, with no console errors.
- **Status: done.** Six views in the header: Map, Territories, Holders, Table, Church & resources, About & sources. On a phone the view buttons wrap to two rows.
  - **URL state** (`state/store.ts`): `#/territories?h=feudal&lvl=2`, `#/holders?entity=…`, `#/church?layer=abbeys`, `#/table?d=…&r=…&t=…&hd=…&s=…&q=…`.
  - **Territories** (`ui/sideViews.ts`, `model/territories.ts`):
    - Administrative divisions or feudal realms, one level at a time or all levels.
    - Divisions are drawn grey; realms are coloured by kind (county, lordship/terre/fief, church lands).
    - The list gives each area's kind and number of places.
    - Areas are hovered and clicked on the map, and the smallest area under the pointer wins.
    - The panel opens with the area outlined.
  - **Links** (`ui/navigate.ts`):
    - A territory picked from any list opens Territories at its hierarchy and level, with the map fitted to it.
    - A village picked from the table or a thematic list opens the map, zoomed in on it.
  - **Place panel:** a territory's members are now in the book's order, each with its entry number.
  - **Table** (`ui/pages.ts`):
    - Every entry in the book's order: number, text, place, district, realm, section or list, holders and page.
    - Filters by district (with the divisions below it), realm, section, holder, list and words.
    - CSV export of the filtered rows. The toolbar stays in view.
    - Domain and safeguard entries without a named holder count as the duke's.
  - **Holders:** pick any holder to see the realms they hold and their places by tenure. The map colours those places, hatched where held in part, and draws the realms.
  - **Church & resources:**
    - Towns, cathedrals and collegiates, abbeys (with their order), priories, convents and commanderies, as the book's thematic lists.
    - Each entry links to its place, which is coloured on the map.
    - The chaumes are listed by provostship with their gîtes, and are not located.
  - **About & sources** (`ui/about.ts`), in four languages:
    - the book and its 1870 edition (signed "H. L. et A. de B.")
    - what the map shows and doesn't
    - how the data was made
    - sources and terms, with the data version and coverage
  - Checked by screenshot, with no console errors: every view in EN/FR/DE/JA at 1280 px and at 390 × 844. Also checked in a browser:
    - table → map
    - holder → territory
    - table filters from the URL
  - Tests: 20 vitest tests, adding territory levels, the table's holders and filters, and the new URL keys.

### Stage 10: QA & polish
- Tasks:
  - Port hist_map's Playwright suites (`core`, `views`, `layout`, `a11y`, `perf`) without the year tests.
  - Add tests for: the place panel listing several entries; a split place; the territory levels; table filters and CSV export.
- Done when: `make e2e` passes, and axe reports no serious or critical violations.
- **Status: done.** `make e2e` starts the dev server and runs Playwright in its container (`web/playwright.config.ts`, `web/e2e/`). There are 45 tests, about 45 s, stable over repeated runs.
  - **core:**
    - the colour modes
    - the language switch (interface and place names)
    - Saint-Avold's panel: four entries with numbers and pages, and two holdings
    - Athienville, split between the prévôtés of Einville and Lunéville: two district chains
    - keyboard focus into and out of the panel, and the skip link to the table
    - the tooltip kept inside the map
    - the shapes of places
  - **views:**
    - the territory hierarchies and levels
    - walking down a level from the panel and back up
    - a realm link fitted on the map
    - the holder picker
    - the table filters, its sticky toolbar and headers, the CSV export, and a place opened zoomed on the map
    - Church & resources, and the About page in four languages
  - **layout** (desktop and Pixel 7): ten view states are never wider than the screen and log no errors. **a11y:** axe (WCAG 2.1 A/AA) on the same ten states.
  - **perf:** data load 0.3 s, first render under 20 ms, mode changes under 15 ms, table about 0.1 s. The budgets are 3 s, 200 ms and 1.5 s.
  - Fixed on the way:
    - Territory links in the place panel now open the Territories view at their hierarchy and level, as list links do.
    - The skip link ("Skip the map: show the entries as a table") was missing.
    - The About page's scroll area takes keyboard focus. This was axe's only finding.

### After Stage 10: the index and the lists, number by number
Requested after Stage 10: the index's names and the lists' names don't always match; go through both, match the numbers, register the spellings in the app, and check where the places are (the commune the index gives).
- **Status: done.**
  - **Both ways** (`curate/reconcile.py`): every number printed on every index line is resolved to the entry it means.
    - First the entries the line claims, on their own number or on the number they were misread as.
    - Then an entry whose name or text names the line's place, at the number or a confusable one: one digit away, or digits the scan confuses ("554" for 334).
    - An abbreviated number ("1357, 95") counts from the entry the number before it means, not from that number as the scan read it.
    - A line that claims an entry by name alone gives way to a line that prints its number.
  - **By hand:** about 130 decisions in `data/curated/manual/index_numbers.csv` (page, index line, number as read, entry meant, note).
    - Each number was read again on the printed page (cropped from the PDF), with the editor's corrections and the table of old forms.
    - "Flainval, 38": the scan reads 58. "Croismare, 255": Hadonviller, its old name. "Kaisen, 1497" replaces Kassheim (corrections).
    - Where a clearly printed number leads to an entry that another line names (Fosses, 2154: Drulben is Trulben), the line is left without an entry and says why.
    - A "not:N" decision removes a claim by name alone.
  - **Result** (`data/review/index_numbers.csv`, one row per number and per unnamed entry; summary in `report.md`):
    - numbers: 1,919 agree, 89 spelling differs, 358 corrected automatically, 96 decided by hand, 30 without an entry, 0 unresolved
    - entries: Dénombrement entries matched to an index line went from 95.0% to 98.3%; 38 entries are named by no line; 39 entries name more than one place
  - **Spellings** in the app: the place panel lists them by source, each with its entries.
    - in the lists (the book), in the editor's index (1870), in the table of old forms (323 places)
    - An entry naming several places lists the others as links; the table shows every place of an entry.
  - **Locations** (`geo/geocode.py`):
    - The index's communes and cantons, garbled by the scan now and then ("Bouzonviiie", "Yal-d'Ajol", "Sainl-Dié"), are set to the spelling the index prints most. Only names that show the scan's damage change.
    - Every located place is checked against its commune or canton. Among namesakes (three Colombeys, two Saint-Nicolas) the one nearest the place's district is meant; a compound name counts ("Thiaucourt" is Thiaucourt-Regniéville).
    - A match far from it is made again near it: 14 places (Saint-Nicolas-de-Port, Aboncourt near Colombey-les-Belles, Hamonville, Lamorville…); 38 are flagged, and 74 name a commune or canton no database has.
    - A strong match near the index's commune or canton is no longer moved by the district pass; places set in `rules.yaml` (new `geocode` section) are left alone by the automatic passes.
    - 1,720 of 1,901 settlements are located, 95.7% of those the index identifies.
  - Tests: 5 more pytest tests (`tests/test_reconcile.py`), 2 more Playwright tests (spellings by source; an entry naming two places). 75 pytest, 20 vitest and 47 Playwright tests pass.

### After Stage 10: settlements in several territories, as in hist_map
Requested: membership of settlements to divisions and realms isn't clear-cut; record a settlement's memberships in every territory it belongs to, the way hist_map does.
- **Status: done.**
  - **Rows from the lists** were already one per territory (a village "en partie" under two prévôtés, a fief's village under its office and its lordship): 186 settlements are in two divisions, 16 in three, and 9 in two realms.
  - **`manual/memberships.csv`**, as in hist_map: the memberships the lists don't give, each with its page and why. Applied after the places get their final ids. 7 rows, each a territory's own seat listed elsewhere.
    - the bans of Belmont, Bouxières, Grandvillers and Dompierre, and Saint-Dié
    - the lordship of Varsberg
    - the sous-prévôté of Sierck
    - Not added, because the seat is uncertain: the mairie of Longchamp (three Longchamps), the mairie of Steimbach (only the Steinbach of Saarland is found), and the val of Harol (Harol is the seat of the ban of Harol).
  - **Shared lands of a division and its realm** (hist_map's `split_memberships`, here for the counterpart pairs): the realm's places are in the division, and the division's places are the realm's unless they are in another realm.
    - It adds nothing today: every pair already has the same members, and the 11 places of the castellany of Hombourg and Saint-Avold outside its lordship are the abbey of Saint-Avold's.
    - It keeps future data consistent; the report lists what it adds.
  - **Areas** (`geo/territories.py`), as in hist_map: every membership counts. A settlement in two divisions puts its cell in both areas, which overlap there, and both list it as `shared`.
    - 134 territories have an area (131 before): the bans of Grandvillers and Dompierre, Maizey and Vaudicourt now do. Only the mairie of Steimbach has no located member.
  - Tests: 3 more pytest tests: a settlement in both areas, the shared lands rule, and the manual rows reaching the table.

### After Stage 10: the Map without the Districts and Realms modes
Requested: drop the Districts and Realms modes from the Map, which repeat the Territories view.
- **Status: done.** The Map keeps the Tenure and Holder modes. An old link with `color=district` or `color=realm` opens the Map in Tenure.
  - The tooltip always gives the district chain.
  - The legend always has the hatching key.
  - The code and strings of the two modes are gone: realm kinds per place, the bailliage labels on the Map, the district legend.
  - The Territories view keeps the realm colours.
  - Tests were updated: the Map has two colour tabs, and an old mode in the URL falls back to Tenure.

### After Stage 10: the Tenures tab
Requested: remove the Holder mode from the Map tab, and rename the Map tab to Tenures.
- **Status: done.**
  - The map colours by tenure only. The colour-mode tabs, the holder legend (the three coloured holders, the picker, "reset colours") and the `color=` and `c=` URL keys are gone; the Holders view keeps its own map of one holder's places.
  - The tab is called Tenures, Tenures, Besitzarten and 保有形態. Its URL stays `#/map`, and links from the time of the modes still open it.
  - The performance test now times re-renders by switching the language: up to 7 ms.

### After Stage 10: Territories first
Requested: make Territories the default view, and put Tenures second.
- **Status: done.** The tabs are Territories, Tenures, Holders, Table, Church & resources, About & sources. A bare address or an unknown view opens Territories; `#/map` links still open Tenures. A Playwright test checks the default and the order (48 tests pass).

### After Stage 10: the Territories screen as in hist_map
Requested: make the Territories screen follow the colour scheme and the structure of hist_map's Territories page.
- **Status: done.**
  - **Colours** (`model/territories.ts`, `model/colors.ts`), as in hist_map, in both hierarchies:
    - every realm is coloured by its kind: offices, castellanies and provostships in blue (bailliages, prévôtés, offices, districts, the sous-prévôté, the towns with their districts), lordships and fiefs in orange, counties in green, and the other realms in a dark grey (bans, mairies, vals, the abbey's lands)
    - opacity 0.45 for the hues and 0.75 for the grey, white borders, the selected realm outlined in black, the duchy outlined in black (hist_map's bailiwick line)
    - hist_map's principalities (yellow) and marquisates (violet) don't occur in this book. Church lands, green before, are in the grey group: hist_map has no group for them.
  - **Side list**, as in hist_map:
    - the title with the number shown ("Realms (21)")
    - the hierarchy switch, the level switch, and a "Kind of realm" menu: all kinds by level, or one kind at every level (`#/territories?kind=ban`), grouped as administrative districts and feudal titles, with counts
    - the colour key of the kinds with the number shown of each
    - the realms by name, each with its number of places
    - The notes on divisions and realms and the per-realm swatches are gone, as in hist_map.
  - Not taken from hist_map: the year and the "realms outside the bailiwick" switch, which this book doesn't need.
  - The Territories tab draws only the territories' borders: the villages' cells are hidden there (they stay on the other tabs).
  - The bailliages have a colour of their own: hist_map's violet (its marquisates', which this book doesn't have), the one fourth hue that validates against the other three and the grey. The prévôtés, offices and castellanies inside them stay blue.
  - Tests: vitest for the groups and the kind filter; one more Playwright test (kind menu and key). 19 vitest and 49 Playwright tests pass.

### After Stage 10: lost villages, hamlets and farms checked
Requested after Scheuer-Hof (placed in Luxembourg instead of at Nohn): check the other lost villages, hamlets and farms.
- **Status: done.** An audit compared every located settlement with what the index says.
  - **The checks:**
    - a lost place matched by name
    - more than 6 km from the commune the index names (the nearest place of that name)
    - a modern country that contradicts the index's département or state
    - a hamlet, farm or mill more than 25 km from its district's other places
  - **The result:** 121 places flagged. Most were false alarms:
    - towns "lost" through a misparsed index line (Xertigny, Pirmasens, Rugney)
    - the large Saarland municipalities, whose villages lie 6–10 km from the centre
    - enclaves far from the rest of their district (Rémelange, Saint-Privat)
  - **44 fixes in `rules.yaml` (`geocode`):**
    - 41 hamlets, farms and lost places matched to a namesake 15–160 km away are now placed at the commune the index gives. Examples:
      - the hamlets of Harol (the scan reads "Haro")
      - Moniet, the old priory near Deneuvre
      - the stud farm of Portieux, at Rosières-aux-Salines
      - Saint-Epvre and Viller, the suburbs of Toul and Lunéville
      - Rohr, absorbed by Bitche
      - the Mandrays at Mandray
      - Maisons-de-Raon at Bellefontaine
    - 3 are left unlocated: Bury and la Ruelle, for which the index gives no commune, and Dittclingen, "emplacement inconnu".
  - **The new rule `{at: commune}`:** places a hamlet at its commune, approximate (hollow), choosing among namesakes the one nearest the place's district. A place put at another place now takes that place's country.
  - A pytest test covers the rule (79 pytest, 49 Playwright tests pass).

### After Stage 10: blank land only for known foreign lands
Requested after a question about the holes west of Forbach (the Warndt): how does hist_map treat modern communes the book doesn't list? It ignores them, and only the book's places divide the land. Three ways were tried: neutral points for every unlisted commune (until now), none (hist_map's way), and neutral points only in known foreign lands. The third was chosen.
- **Status: done.**
  - **Before:** every Wikidata commune the book doesn't list took land of its own, so modern or unlisted villages cut holes into the duchy (Creutzwald, Carling, Porcelette in the Warndt; Stiring-Wendel).
  - **hist_map's way alone** closed the holes, but painted the Pays messin as the duchy's.
  - **Now** (`geo/territories.py`, `data/curated/manual/foreign_lands.csv`): as in hist_map, only the book's places divide the land, except inside the foreign lands listed by hand, each a circle around its town with a note:
    - Metz and the Pays messin (15 km)
    - Toul (8 km) and Verdun (12 km)
    - the bishop of Metz's lands around Vic (7 km), Rambervillers (5 km), Baccarat (4 km)
    - Liverdun, of the bishops of Toul (4 km)
    - Nassau-Saarbrücken (8 km; 12 km reached into the Lorraine villages east of Forbach)
  - Inside them, unlisted communes are neutral points with land of their own. The book's own places always count as Lorraine's, so the duchy's villages in the Pays messin stay islands.
  - Coume (entry 1360, the scan's "Ceume") and Boucheporn (2273, "Banschborn", which the index prints as 2275) were located on the way.
  - The circles are a rough stand-in for borders; each is adjusted in the CSV. The About page describes the method in four languages.

### After Stage 10: the Settlements tab, the default view
Requested: rename Tenures to Settlements and make it the default view.
- **Status: done.** The tab is Settlements, Localités, Orte, 集落. A bare address or an unknown view opens it, and it is the first tab, before Territories. Its URL stays `#/map`.

### After Stage 10: administrative levels by kind of division
Requested: the district of Bitche and the other first-level offices showed among the bailliages, and their mairies among the prévôtés and offices.
- **Status: done.** Administrative levels came from the depth below the duchy. They now follow the kind of division (`geo/territories.py`, `ADMIN_LEVELS`), never above the parent's level plus one:
  - 1: bailliages
  - 2: prévôtés, offices, castellanies, districts, the towns with their districts
  - 3: bans, mairies, vals
  - Subdivisions of a prévôté stay one level below it (the district of Perl and the sous-prévôté in the prévôté of Sierck, Rimling in the district of Bitche: 3).
  - The bailliages level now shows the eight bailliages only; the lands outside them appear from level 2. Feudal realms keep levels by depth.

### After Stage 10: terminology as in hist_map
Requested: name bailiwicks, provostships and the other units as hist_map does.
- **Status: done.**
  - English uses the English terms, not the French ones: Bailiwicks; Provostships, offices; Bans, mayoralties; valley districts.
  - German follows hist_map:
    - bailiwick: Bellistum (Oberamt); territories are named "Bellistum Nancy"
    - provostship: Schultheißerei; sub-provostship: Unterschultheißerei
    - the hierarchies: Verwaltungsgliederung and Lehnsherrschaften
  - French follows hist_map:
    - lordship: seigneurie ("Seigneurie de Bitche", no longer "Terre et seigneurie de Bitche")
    - the hierarchies: Circonscriptions administratives and Seigneuries et fiefs
    - the rural provostship: prévôté rurale
  - Vocabulary (`vocab.yaml`), the territories' generated names, the interface strings and the About page were changed together; ids are unchanged.

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
