"""Load the curated dataset (vocab.yaml + one CSV per table)."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from denombrement import config
from denombrement.data.models import TABLES, Entity, Entry, Feature, Holding, IndexLink, Membership, Place

LANGS = ("en", "fr", "de", "ja")


@dataclass
class Issue:
    level: str  # "error" | "warning" | "info"
    table: str
    row: int | None  # CSV line number (header is line 1)
    message: str

    def __str__(self) -> str:
        where = f"{self.table}.csv:{self.row}" if self.row else f"{self.table}"
        return f"{self.level.upper():7} {where}: {self.message}"


@dataclass
class Dataset:
    vocab: dict[str, dict[str, dict]]
    entries: list[tuple[int, Entry]] = field(default_factory=list)
    places: list[tuple[int, Place]] = field(default_factory=list)
    memberships: list[tuple[int, Membership]] = field(default_factory=list)
    entities: list[tuple[int, Entity]] = field(default_factory=list)
    holdings: list[tuple[int, Holding]] = field(default_factory=list)
    features: list[tuple[int, Feature]] = field(default_factory=list)
    index_links: list[tuple[int, IndexLink]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)  # parse errors found while loading


def load_vocab(path: Path) -> dict[str, dict[str, dict]]:
    return yaml.safe_load(path.read_text())


def load(directory: Path = config.CURATED_DIR) -> Dataset:
    ds = Dataset(vocab=load_vocab(directory / "vocab.yaml"))
    for model in TABLES:
        path = directory / f"{model.table}.csv"
        if not path.exists():
            ds.issues.append(Issue("warning", model.table, None, "file missing (treated as empty)"))
            continue
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            unknown = set(reader.fieldnames or []) - set(model.model_fields)
            if unknown:
                ds.issues.append(Issue("error", model.table, 1, f"unknown columns: {sorted(unknown)}"))
                continue
            rows = getattr(ds, model.table)
            for line, raw in enumerate(reader, start=2):
                if not any((v or "").strip() for v in raw.values()):
                    continue  # blank line
                try:
                    rows.append((line, model.model_validate(raw)))
                except ValidationError as e:
                    for err in e.errors():
                        loc = ".".join(map(str, err["loc"])) or "row"
                        ds.issues.append(Issue("error", model.table, line, f"{loc}: {err['msg']}"))
    return ds
