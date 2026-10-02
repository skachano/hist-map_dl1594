"""Read the editor's entry numbers through the OCR's misreadings, using the sequence.

The numbers run from 1 to 2487 without gaps. A token at the start of a line is scored against
each candidate number by an alignment cost in which the misreadings this scan makes are cheap
(3 and 5, 1 and 4, letters for digits, stray symbols), and the candidate that best continues
the sequence wins.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

# Digit pairs the OCR confuses in this font.
_CONFUSED = {frozenset(p) for p in ("35", "14", "17", "56", "68", "38", "69", "05", "09", "06", "89")}
# Letters and symbols read for a digit.
_LOOKALIKE = {
    "l": "1", "I": "1", "i": "1", "!": "1", "|": "1", "t": "1", "f": "1", "J": "1", "j": "1",
    "ï": "1", "î": "1", "Î": "1", "Ï": "1", "O": "0", "o": "0", "Q": "0", "D": "0", "G": "6", "b": "6",
    "S": "5", "s": "5", "z": "2", "Z": "2", "B": "8", "g": "9", "q": "9", "a": "2", "H": "4", "A": "4",
}
_JUNK = set("»«*'’:;%&()<>?•·^\"-_~,{}[]/\\$")  # read for a digit, or noise around one

SUBST_CONFUSED = 0.3
SUBST_LOOKALIKE = 0.2
SUBST_JUNK = 0.5
SUBST_OTHER = 1.0
INDEL = 0.7
GAP_PENALTY = 1.0      # per number skipped: the numbering has no gaps
MAX_COST = 1.5         # beyond this a token does not read as the number
LOOKAHEAD = 6          # how many numbers ahead a token may jump


def _sub(c: str, d: str) -> float:
    if c == d:
        return 0.0
    if c.isdigit():
        return SUBST_CONFUSED if frozenset(c + d) in _CONFUSED else SUBST_OTHER
    if _LOOKALIKE.get(c) == d:
        return SUBST_LOOKALIKE
    if _LOOKALIKE.get(c) and frozenset(_LOOKALIKE[c] + d) in _CONFUSED:
        return SUBST_LOOKALIKE + SUBST_CONFUSED
    if c in _JUNK:
        return SUBST_JUNK
    return SUBST_OTHER


@lru_cache(maxsize=200_000)
def cost(token: str, number: int) -> float:
    """Alignment cost of reading `token` as `number`."""
    a, b = token, str(number)
    prev = [j * INDEL for j in range(len(b) + 1)]
    for i in range(1, len(a) + 1):
        # A junk symbol costs less to drop than a letter or digit.
        drop = INDEL * (0.5 if a[i - 1] in _JUNK else 1.0)
        cur = [prev[0] + drop]
        for j in range(1, len(b) + 1):
            cur.append(min(prev[j] + drop, cur[j - 1] + INDEL, prev[j - 1] + _sub(a[i - 1], b[j - 1])))
        prev = cur
    return prev[-1]


_TOKEN = re.compile(r"^\s*(\S{1,6}?)\s?\.\s?(?=\S)")
_TOKEN_NO_STOP = re.compile(r"^\s*(\d{2,4}\S{0,2})\s+(?=[A-ZÀ-Ý])")  # "221S< Ranschborn.", "252L Vaudémont."


def leading_token(text: str) -> str | None:
    """The token before the first full stop of a line ("1546" in "1546. Kelternostern."), if short."""
    m = _TOKEN.match(text) or _TOKEN_NO_STOP.match(text)
    if not m or (m.re is _TOKEN_NO_STOP and sum(c.isdigit() for c in m.group(1)) < 3):
        return None
    tok = m.group(1)
    if not any(c.isdigit() or c in _LOOKALIKE or c in _JUNK for c in tok):
        return None
    return tok


@dataclass
class Reading:
    number: int
    cost: float
    skipped: int  # numbers jumped over


def read(token: str, previous: int, last: int) -> Reading | None:
    """The best reading of `token` as one of the next numbers after `previous`, or None."""
    best: Reading | None = None
    for n in range(previous + 1, min(previous + 1 + LOOKAHEAD, last + 1)):
        c = cost(token, n) + GAP_PENALTY * (n - previous - 1)
        if best is None or c < best.cost:
            best = Reading(n, c, n - previous - 1)
    if best and best.cost <= MAX_COST:
        return best
    return None


REJECT_CLEAN = 2.0     # treating a clean number ("47") as not an entry
REJECT_GARBLED = 0.8   # treating a garbled token ("Et", "Mi") as not an entry
BEAM = 60


def assign(tokens: list[str | None], last: int) -> list[Reading | None]:
    """Read all line-start tokens at once: the increasing numbering with the least total cost.

    Each token is either one of the next numbers after the previous entry (its alignment cost,
    plus GAP_PENALTY per number skipped) or not an entry at all (REJECT_*). A beam search keeps
    the best states, keyed by the last number assigned; greedy reading can't recover from one
    wrong pick, this can.
    """
    states: dict[int, tuple[float, int]] = {0: (0.0, -1)}  # last number -> (cost, history index)
    history: list[tuple[int, Reading | None]] = []          # (previous history index, reading)
    for tok in tokens:
        if tok is None:
            continue
        new: dict[int, tuple[float, int]] = {}
        reject = REJECT_CLEAN if tok.isdigit() else REJECT_GARBLED
        for m, (c, h) in states.items():
            options = [(m, c + reject, None)]
            for n in range(m + 1, min(m + 1 + LOOKAHEAD, last + 1)):
                k = cost(tok, n)
                if k <= MAX_COST:
                    options.append((n, c + k + GAP_PENALTY * (n - m - 1), Reading(n, k, n - m - 1)))
            for n, cn, reading in options:
                if n not in new or cn < new[n][0]:
                    history.append((h, reading))
                    new[n] = (cn, len(history) - 1)
        states = dict(sorted(new.items(), key=lambda kv: kv[1][0])[:BEAM])
    end = min(states.items(), key=lambda kv: kv[1][0])
    readings: list[Reading | None] = []
    h = end[1][1]
    while h >= 0:
        prev, reading = history[h]
        readings.append(reading)
        h = prev
    readings.reverse()
    out: list[Reading | None] = []
    it = iter(readings)
    for tok in tokens:
        out.append(next(it) if tok is not None else None)
    return out


FILL_MAX_COST = 2.2   # a number found in the gap between two numbered neighbours may be read more loosely
# A number inside a line: after a full stop, or at the start ("Sainct-Remvmonl.1156. Allainville.").
_INNER = re.compile(r"(?:^|(?<=[.;:{}|]))\s*(?P<tok>[^\s.]{1,6}?(?: [^\s.]{1,2})?)\s?[.,^<]\s?(?=[^\W\d_]|')")


def _numberish(tok: str, force: bool = False) -> bool:
    """A token that can be a misread number, not a word ("ttïA", "liVJ", not "Item"): at most
    one letter that doesn't stand for a digit. With `force`, any token of one or two characters
    ("V" for 1)."""
    if force and len(tok) <= 2:
        return True
    others = sum(c.isalpha() and c not in _LOOKALIKE for c in tok)
    return any(c.isdigit() or c in _LOOKALIKE or c in _JUNK for c in tok) and others <= 1


def find_in(text: str, number: int, start: int = 0, force: bool = False) -> tuple[int, int, str] | None:
    """Where `number` starts inside `text` (from `start`): (token start, body start, token).
    With `force`, the first number-like token is taken whatever its cost (one number is missing
    between two neighbours, and this is the only place it can be)."""
    for m in _INNER.finditer(text, start):
        tok = m.group("tok")
        if _numberish(tok, force) and (force or cost(tok, number) <= FILL_MAX_COST):
            return m.start("tok"), m.end(), tok
    return None
