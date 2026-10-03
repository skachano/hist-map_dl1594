"""The index and the lists, number by number, in both directions.

The editor's index ("Table des noms de lieux") sends each place to the numbers of the entries that
name it; the lists give each entry its number and the book's spelling. The two don't always
agree: the scan misreads the index's numbers (3 and 5, 1 and 4…), the printer misprinted some,
and one entry can name several places ("Volfflingen et Weissweiler"), each with its index line.

Matching runs entry by entry (`build.Matcher`). This resolves every number printed on every index
line to the entry it means:

1. the entries the line claims (the matcher's matches), on the number printed, or on the printed
   number they are a misreading of (`corrected`);
2. a free number leading to an entry whose name or text names the line's place, or to an entry
   one misread digit away that does (`corrected`);
3. a free number leading to an entry no line claims, with a spelling the editor identified
   (`spelling differs`);
4. what is left is decided by hand in `data/curated/manual/index_numbers.csv`
   (page, index_name, printed, entry: the entry meant, blank for none; note).

Writes `data/review/index_numbers.csv`: one row per printed number and per entry no line names.
"""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from denombrement import config
from denombrement.parse import numbering
from denombrement.text import indexes

FIELDS = ["status", "index_page", "index_name", "printed", "number", "entry", "entry_name", "entry_page",
          "similarity", "place_id", "note"]
MANUAL = config.CURATED_DIR / "manual" / "index_numbers.csv"
GOOD = 0.75        # a name that fits: same place, another spelling
FAIR = 0.3         # the editor's identification of a spelling that looks different


@dataclass
class Link:
    row: object                       # the index line (corrections.IndexRow)
    entry: int | None                 # None: the number leads to no entry
    printed: str                      # the number as printed
    status: str                       # agrees, spelling differs, corrected, manual, unresolved, no entry
    sim: float = 0.0
    note: str = ""


@dataclass
class Resolution:
    links: list[Link] = field(default_factory=list)
    unnamed: list[int] = field(default_factory=list)   # Dénombrement entries no line names

    def by_entry(self) -> dict[int, list[Link]]:
        out = defaultdict(list)
        for x in self.links:
            if x.entry is not None and x.status not in ("unresolved", "no entry"):
                out[x.entry].append(x)
        return out


def _key(text: str) -> str:
    from denombrement.curate.build import name_key
    return name_key(text)


def load_manual() -> dict[tuple[str, str, str], dict]:
    if not MANUAL.exists():
        return {}
    return {(r["page"], _key(r["index_name"]), r["printed"].strip()): r for r in csv.DictReader(MANUAL.open())}


def text_sim(e: dict, row, sim, similarity) -> float:
    """How well the entry names the line's place: its name, or a run of one to three words of
    its text ("…aliàs Longeville", "Volfflingen et Weissweiler")."""
    best = sim(e["name"], row)
    if best >= GOOD:
        return best
    words = re.findall(r"[^\s,.;:()]+", e["text"])
    want = len(_key(row.entry.name))
    for k in (1, 2, 3):
        for i in range(len(words) - k + 1):
            w = " ".join(words[i:i + k])
            # a run about as long as the name: "Sainct" alone is not "Saint-Dié"
            if len(_key(w)) >= max(4, 0.6 * want):
                best = max(best, similarity(w, row.entry.name))
    return best


def neighbours(n: int) -> set[int]:
    """Numbers one digit away from `n`: one changed, dropped or added."""
    s = str(n)
    out = set()
    for i in range(len(s) + 1):
        for d in "0123456789":
            out.add(s[:i] + d + s[i:])                      # added
            if i < len(s):
                out.add(s[:i] + d + s[i + 1:])              # changed
        if i < len(s):
            out.add(s[:i] + s[i + 1:])                      # dropped
    return {int(x) for x in out if x and not x.startswith("0")} - {n}


def _tokens(ie) -> list[str]:
    raw = [t.strip() for t in ie.numbers_raw.split(",")] if ie.numbers_raw else []
    return raw if len(raw) == len(ie.numbers) else [str(n) for n in ie.numbers]


def _slot_of(links: list[Link], slots: list[tuple[int, str]]) -> list[int | None]:
    """The slot each link took (by its printed token), in order."""
    taken, out = set(), []
    for x in links:
        i = next((i for i, (_, tok) in enumerate(slots) if tok == x.printed and i not in taken), None)
        if i is not None:
            taken.add(i)
        out.append(i)
    return out


def _near(token: str, n: int, m: int) -> bool:
    """Could the index have printed (or the scan read) `token` for entry `m`?"""
    from denombrement.curate.build import variants_of
    return m in variants_of(n) or numbering.cost(token, m) <= 1.0


def resolve(index_rows, entries: list[dict], matches: dict, sim, similarity) -> Resolution:
    by_no = {e["no"]: e for e in entries}
    claims: dict[int, list[int]] = defaultdict(list)
    for no, m in sorted(matches.items()):
        if m.row is not None:
            claims[id(m.row)].append(no)
    claimed = {no for nos in claims.values() for no in nos}
    manual = load_manual()
    res = Resolution()
    for r in index_rows:
        ie = r.entry
        slots = list(zip(ie.numbers, _tokens(ie)))
        free = list(range(len(slots)))
        links: list[Link] = []
        # 0. decided by hand
        for i in list(free):
            n, tok = slots[i]
            d = manual.get((r.page, _key(ie.name), tok)) or manual.get((r.page, _key(ie.name), str(n)))
            if d is not None:
                no = int(d["entry"]) if d["entry"].strip() else None
                links.append(Link(r, no, tok, "manual" if no else "no entry", 1.0, d.get("note", "")))
                free.remove(i)
        # A number decided to lead to no entry takes the line's claim on that entry with it
        # (the editor's corrections drop "Kassheim, 1497" for "Kaisen, 1497").
        # a number decided by hand no longer means its own entry ("58" that is 38)
        dropped = {n for (n, tok) in slots if any(x.printed == tok and x.entry != n for x in links)}
        # "not:N": the line names the entry by neither number nor name (the matcher's claim is wrong)
        dropped |= {int(k[2][4:]) for k in manual if k[0] == r.page and k[1] == _key(ie.name) and k[2].startswith("not:")}
        mine = [c for c in claims[id(r)] if not any(x.entry == c for x in links) and c not in dropped]
        # 1. the claimed entries on their own numbers…
        for c in list(mine):
            i = next((i for i in free if slots[i][0] == c), None)
            if i is not None:
                s = sim(by_no[c]["name"], r)
                links.append(Link(r, c, slots[i][1], "agrees" if s >= 0.5 else "spelling differs", s))
                free.remove(i)
                mine.remove(c)
        # …or on the number they were misread as
        for c in mine:
            i = min(free, key=lambda i: numbering.cost(slots[i][1], c), default=None)
            if i is not None and (_near(slots[i][1], slots[i][0], c) or numbering.cost(slots[i][1], c) <= 2.0):
                links.append(Link(r, c, slots[i][1], "corrected", sim(by_no[c]["name"], r)))
                free.remove(i)
            else:
                links.append(Link(r, c, "", "corrected", sim(by_no[c]["name"], r), "number not printed in the index"))
        # An abbreviated number ("1357, 95") counts from the entry the number before it means,
        # not from that number as the scan read it ("1557, 95" is not 1595).
        meant = {i: x.entry for i, x in zip(_slot_of(links, slots), links) if i is not None and x.entry}
        for i in list(free):
            n, tok = slots[i]
            digits = re.sub(r"\D", "", tok)
            prev = next((meant[j] for j in range(i - 1, -1, -1) if j in meant), None)
            if digits and prev and len(digits) < len(str(prev)):
                m = indexes._full(int(digits), prev)
                if m != n and m in by_no and text_sim(by_no[m], r, sim, similarity) >= 0.45:
                    links.append(Link(r, m, tok, "corrected", text_sim(by_no[m], r, sim, similarity),
                                      f"abbreviated after {prev}"))
                    meant[i] = m
                    free.remove(i)
        # 2./3. the numbers left
        for i in free:
            n, tok = slots[i]
            e = by_no.get(n)
            s = text_sim(e, r, sim, similarity) if e else 0.0
            if e and s >= GOOD:
                links.append(Link(r, n, tok, "agrees", s))
                continue
            # one digit away, or several digits the scan confuses ("554" for 334)
            cands = {m for m in neighbours(n) if m in by_no and _near(tok, n, m)}
            width = len(re.sub(r"\D", "", tok)) or len(tok)
            cands |= {m for m in by_no if isinstance(m, int) and len(str(m)) == width and numbering.cost(tok, m) <= 1.0}
            near = [(text_sim(by_no[m], r, sim, similarity), m) for m in cands - {n}]
            near = [x for x in near if x[0] >= GOOD + 0.05]
            if near:
                s2, m = max(near)
                links.append(Link(r, m, tok, "corrected", s2))
            elif e and n not in claimed and s >= FAIR:
                links.append(Link(r, n, tok, "spelling differs", s, "check: the entry no line claims"))
            elif e is None:
                links.append(Link(r, None, tok, "no entry", 0.0, f"no entry {n}"))
            else:
                links.append(Link(r, n, tok, "unresolved", s, f"entry {n} is {e['name']}"))
        res.links += links
    # A line that claims an entry by name alone gives way to a line that prints its number
    # (the corrections make "Rorbach, 1631" Petit-Rohrbach: Forbach doesn't keep it by its name).
    printed = {x.entry for x in res.links if x.printed and x.entry and x.status not in ("unresolved", "no entry")}
    res.links = [x for x in res.links if x.printed or x.entry not in printed]
    named = {x.entry for x in res.links if x.status not in ("unresolved", "no entry")}
    res.unnamed = [e["no"] for e in entries if e["series"] == "main" and e["no"] not in named]
    return res


def write(res: Resolution, entries: list[dict], place_of_row: dict[int, str]) -> Counter:
    by_no = {int(e["no"]): e for e in entries}
    rows = []
    for x in res.links:
        e = by_no.get(x.entry) if x.entry else None
        rows.append({"status": x.status, "index_page": x.row.page, "index_name": x.row.entry.name, "printed": x.printed,
                     "number": "", "entry": x.entry or "", "entry_name": e["name"] if e else "",
                     "entry_page": e["source_page"] if e else "", "similarity": f"{x.sim:.2f}",
                     "place_id": place_of_row.get(id(x.row), ""), "note": x.note})
    for no in res.unnamed:
        e = by_no[no]
        rows.append({"status": "not in index", "entry": no, "entry_name": e["name"], "entry_page": e["source_page"],
                     "place_id": e["place_id"]})
    order = ["unresolved", "not in index", "no entry", "manual", "corrected", "spelling differs", "agrees"]
    rows.sort(key=lambda r: (order.index(r["status"]), int(r["entry"] or 0), r.get("index_name") or ""))
    path = config.DATA_DIR / "review" / "index_numbers.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return Counter(r["status"] for r in rows)


def report(counts: Counter) -> list[str]:
    lines = ["", "## Index and lists, number by number", "",
             "Every number printed in the index resolved to the entry it means, and every entry of the "
             "Dénombrement checked for an index line (`data/review/index_numbers.csv`; decisions in "
             "`data/curated/manual/index_numbers.csv`):", ""]
    return lines + [f"- {k}: {counts[k]}" for k in ("agrees", "spelling differs", "corrected", "manual", "no entry",
                                                    "unresolved", "not in index") if counts[k]]
