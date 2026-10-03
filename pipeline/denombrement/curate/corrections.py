"""Apply the editor's corrections (Stage 1, `corrections.csv`) to the index and the old forms.

Only items marked `auto` are applied: replace a wording, renumber, add an entry, delete an entry.
An item applies to the row named by its `article` on its target page (or the page next to it);
`old`/`new` of a replacement are matched in the row's text. Each item reports what it did.
"""
from __future__ import annotations

import csv
import difflib
import re
from dataclasses import dataclass, field

from denombrement import config
from denombrement.text import indexes


@dataclass
class IndexRow:
    page: str
    entry: indexes.IndexEntry
    deleted: bool = False
    corrected: list[str] = field(default_factory=list)   # what the corrections changed


def _letters(text: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", text)
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if not unicodedata.combining(c)).lower())


def _index_lines() -> dict[tuple[str, str], list[str]]:
    """rules.yaml `index_lines`: index lines the scan misread or merged, as printed. Keyed by
    "page|name as read"; each value is the printed text of one line or a list of lines."""
    import yaml
    path = config.CURATED_DIR / "rules.yaml"
    rules = (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}
    out = {}
    for key, text in (rules.get("index_lines") or {}).items():
        page, _, name = str(key).partition("|")
        out[(page, name)] = text if isinstance(text, list) else [text]
    return out


def load_index() -> list[IndexRow]:
    rows = []
    fixes = _index_lines()
    for r in csv.DictReader((config.RAW_DIR / "index.csv").open()):
        if (r["page"], r["name"]) in fixes:   # read again on the printed page
            for text in fixes.pop((r["page"], r["name"])):
                e = indexes.parse_entry(r["page"], text)
                e.note = "read again on the printed page (rules.yaml index_lines)"
                rows.append(IndexRow(r["page"], e))
            continue
        e = indexes.parse_entry(r["page"], r["text"])
        # Keep Stage 1's second reading of the numbers.
        if r["numbers_source"]:
            e.numbers = [int(n) for n in r["numbers"].split("|") if n]
            e.numbers_ok, e.numbers_source = r["numbers_ok"] == "1", r["numbers_source"]
        e.note = r["note"]
        rows.append(IndexRow(r["page"], e))
    if fixes:
        raise ValueError(f"rules.yaml index_lines: no index line {sorted(fixes)}")
    return rows


def load_old_forms() -> list[dict]:
    return [dict(r) for r in csv.DictReader((config.RAW_DIR / "old_forms.csv").open())]


def pages_near(page: str) -> set[str]:
    """The page a correction cites, its neighbours, and the pages it reads as when the OCR
    misread a 3 as 5 or the reverse ("p. 258" for 238)."""
    if not page.isdigit():
        return {page}
    out = {page}
    for i, d in enumerate(page):
        if d in "35":
            out.add(page[:i] + ("5" if d == "3" else "3") + page[i + 1:])
    return {str(int(p) + k) for p in out for k in (-1, 0, 1)}


def _bare(name: str) -> str:
    """A name without its note call or bracketed remark: "Sanbach* (et non Sambach)" -> "Sanbach"."""
    return _letters(re.split(r"[*(]", name)[0])


def _find(rows: list[IndexRow], article: str, page: str) -> IndexRow | None:
    """The live row named `article` on `page` (or a page near it)."""
    if not article:
        return None
    key = _letters(article)
    live = [r for r in rows if not r.deleted and r.page in pages_near(page)]
    names = {_bare(r.entry.name): r for r in live}
    hit = difflib.get_close_matches(key, list(names), n=1, cutoff=0.7)
    return names[hit[0]] if hit else None


def apply(rows: list[IndexRow], old_forms: list[dict]) -> list[str]:
    """Apply the machine-applicable corrections in place; return one line per item."""
    log = []
    for c in csv.DictReader((config.RAW_DIR / "corrections.csv").open()):
        if c["auto"] != "1":
            log.append(f"- {c['no']} (p. {c['target_page']}, {c['action']}): left for review — {c['text'][:100]}")
            continue
        action, page = c["action"], c["target_page"]
        entries = [e.strip() for e in c["entries"].split(" | ") if e.strip()]
        done = ""
        if c["target"] == "old-forms":
            for text in entries:
                form = indexes.split_old_form(text)
                if form.ok:
                    old_forms.append({"page": page, "old": form.old, "modern": form.modern, "ok": "1", "text": text})
                    done = f"added old form {form.old} → {form.modern}"
        elif action == "add":
            for text in entries:
                text = re.sub(r"\s*\((?:doit |remplace|au lieu|c'est).*?\)\.?\s*$", ".", text)
                rows.append(IndexRow(page, indexes.parse_entry(page, text), corrected=[f"added by correction {c['no']}"]))
                done = f"added {rows[-1].entry.name} {rows[-1].entry.numbers}"
        elif action == "delete":
            row = _find(rows, c["article"], page)
            if row:
                row.deleted = True
                done = f"deleted {row.entry.name}"
        elif action == "renumber":
            row = _find(rows, c["article"], page)
            if row:
                old, new = int(c["old"]) if c["old"] else None, int(c["new"])
                nums = [n for n in row.entry.numbers if n != old] if old else list(row.entry.numbers)
                row.entry.numbers = sorted(set(nums + [new]))
                row.corrected.append(f"correction {c['no']}: {old} → {new}" if old else f"correction {c['no']}: + {new}")
                done = f"{row.entry.name}: {old or '+'} → {new}"
        elif action == "replace":
            row = _find(rows, c["article"], page) if c["article"] else None
            if entries and row:  # "doit être rétabli de la manière suivante : …"
                row.deleted = True
                for text in entries:
                    rows.append(IndexRow(page, indexes.parse_entry(page, text), corrected=[f"restored by correction {c['no']}"]))
                done = f"replaced {row.entry.name} by {', '.join(r.entry.name for r in rows[-len(entries):])}"
            elif c["old"] and c["new"]:
                cands = [r for r in rows if not r.deleted and r.page in pages_near(page)]
                if row:
                    cands = [row] + cands
                old, new = c["old"], c["new"]
                describes = re.search(r"\b(canton|com\.|arr\.|ham\.|vil\.|office|grand duch)", old + " " + new)
                target = row
                if target is None and not describes:
                    # "au lieu de Bcltnach, lisez : Bettnach": the line whose name is closest to the old wording.
                    names = {_letters(r.entry.name): r for r in cands}
                    hit = difflib.get_close_matches(_letters(old.split(",")[0]), list(names), n=1, cutoff=0.7)
                    target = names[hit[0]] if hit else None
                if target is not None and (describes or not old.lower() in target.entry.text.lower()):
                    nums = target.entry.numbers
                    if describes and row is not None:
                        # "art. Métring, au lieu de canton de Faulquemont, lisez : ham., com. de Téting"
                        text = f"{target.entry.name}, {new}, {', '.join(map(str, nums))}."
                    else:
                        # The old wording names the line itself, or is part of its name.
                        rest = target.entry.text.split(",", 1)[1] if "," in target.entry.text else ""
                        new_name = new.split(",")[0].strip()
                        text = f"{new_name},{rest}" if rest else f"{new_name}."
                        if "," in new:
                            text = f"{new}, {', '.join(map(str, nums))}."
                    new_entry = indexes.parse_entry(target.page, text)
                    if not new_entry.numbers:
                        new_entry.numbers, new_entry.numbers_ok = nums, target.entry.numbers_ok
                    target.entry = new_entry
                    target.corrected.append(f"correction {c['no']}: {old} → {new}")
                    done = f"{old} → {new} ({target.entry.name})"
                    cands = []
                for r in cands:
                    if c["old"].lower() in r.entry.text.lower():
                        text = re.sub(re.escape(c["old"]), c["new"], r.entry.text, count=1, flags=re.I)
                        new_entry = indexes.parse_entry(r.page, text)
                        if not new_entry.numbers and r.entry.numbers:
                            new_entry.numbers, new_entry.numbers_ok = r.entry.numbers, r.entry.numbers_ok
                        r.entry = new_entry
                        r.corrected.append(f"correction {c['no']}: {c['old']} → {c['new']}")
                        done = f"{c['old']} → {c['new']} in {r.entry.name}"
                        break
        log.append(f"- {c['no']} (p. {page}, {action}): " + (done or f"NOT APPLIED — {c['text'][:100]}"))
    return log
