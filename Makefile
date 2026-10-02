# All tooling runs in Docker; nothing but Docker is needed on the host.
# Rootless Docker: container root == host user, so no user: mapping is needed.

COMPOSE  := docker compose
PIPELINE := $(COMPOSE) run --rm pipeline
WEB      := $(COMPOSE) run --rm web

.PHONY: help build install dev test test-py test-web info extract validate schema parse curate geocode data pipeline-shell web-shell clean

help:
	@echo "make build          Build the Docker images"
	@echo "make install        Install web dependencies (inside the web container)"
	@echo "make dev            Run the Vite dev server on http://localhost:5174"
	@echo "make test           Run pytest and vitest in containers"
	@echo "make info           Show the pipeline's paths and the source PDF"
	@echo "make extract        Stage 1: PDF -> data/raw/ (pages, parts, index, old forms, corrections)"
	@echo "make parse          Stage 3: parse the Dénombrement -> data/extracted/ (+ parse_report.md)"
	@echo "make curate         Stage 4: rebuild data/curated/*.csv + data/review/report.md"
	@echo "make geocode        Stage 5: coordinates + modern names (Wikidata, GeoNames), then run make curate"
	@echo "make data           parse, curate, geocode, curate: the whole chain after a change to rules.yaml or manual/"
	@echo "make validate       Stage 2: check data/curated/ (FKs, vocab, hierarchies, entry sequence)"
	@echo "make schema         Stage 2: export JSON Schema per table to data/schema/"
	@echo "make pipeline-shell Shell in the pipeline container"
	@echo "make web-shell      Shell in the web container"

build:
	$(COMPOSE) build

web/node_modules: web/package.json web/package-lock.json
	$(WEB) npm ci
	@touch web/node_modules

install: web/node_modules

dev: web/node_modules
	$(COMPOSE) up web

test: test-py test-web

test-py:
	$(PIPELINE) pytest -q

test-web: web/node_modules
	$(WEB) npm test

info:
	$(PIPELINE) python -m denombrement info

extract:
	$(PIPELINE) python -m denombrement extract-text

parse:
	$(PIPELINE) python -m denombrement parse

curate:
	$(PIPELINE) python -m denombrement curate

geocode:
	$(PIPELINE) python -m denombrement geocode

# Geocoding reads the curated places and memberships; curate then merges the coordinates.
data:
	$(PIPELINE) sh -c "python -m denombrement parse && python -m denombrement curate \
	  && python -m denombrement geocode && python -m denombrement curate"

validate:
	$(PIPELINE) python -m denombrement validate

schema:
	$(PIPELINE) python -m denombrement schema

pipeline-shell:
	$(PIPELINE) bash

web-shell:
	$(WEB) bash

clean:
	$(COMPOSE) down --remove-orphans
	rm -rf web/node_modules web/dist
