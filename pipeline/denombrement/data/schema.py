"""Export JSON Schema for each curated table, with vocabulary keys as enums.

The schemas describe one parsed row (lists as arrays, not "|"-joined strings) and can be
reused by Stage 3 as the structured-output format for LLM extraction.
"""
from __future__ import annotations

import json
from pathlib import Path

from denombrement import config
from denombrement.data.models import TABLES, CsvRow, Place
from denombrement.data.store import load_vocab

SCHEMA_DIR = config.DATA_DIR / "schema"


def _enum(prop: dict, keys: list[str]) -> None:
    if prop.get("type") == "array":
        prop["items"] = {"type": "string", "enum": keys}
    elif "anyOf" in prop:  # optional field
        prop["anyOf"] = [{"type": "string", "enum": keys}, {"type": "null"}]
    else:
        prop.pop("type", None)
        prop["enum"] = keys


def table_schema(model: type[CsvRow], vocab: dict) -> dict:
    schema = model.model_json_schema()
    for fld, vocab_name in model.vocab_fields.items():
        _enum(schema["properties"][fld], list(vocab.get(vocab_name, {})))
    if model is Place:  # settlement or territory types
        _enum(schema["properties"]["place_type"], list(vocab.get("place_types", {})) + list(vocab.get("territory_types", {})))
    schema["title"] = model.table
    return schema


def export(out_dir: Path = SCHEMA_DIR) -> list[Path]:
    vocab = load_vocab(config.CURATED_DIR / "vocab.yaml")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for model in TABLES:
        path = out_dir / f"{model.table}.schema.json"
        path.write_text(json.dumps(table_schema(model, vocab), ensure_ascii=False, indent=2) + "\n")
        paths.append(path)
    return paths
