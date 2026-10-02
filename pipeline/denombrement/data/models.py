"""Row models for the curated tables (data/curated/*.csv).

Conventions
- The source describes a single date (1594): no table has years or periods.
- A numbered entry of the book is not a place: one village can appear under several
  numbers (in two prévôtés, as part domain and part fief, in the thematic lists), so
  `entries` and `places` are separate tables, joined by `entries.place_id`.
- Territories belong to one of two hierarchies: administrative divisions (`admin`) and
  feudal realms (`feudal`). Where both cover the same land, both are recorded and linked
  as counterparts (doc/Plan.md §2).
- Territory ids are `<territory type>-<seat>` ("provostship-nancy", "lordship-deneuvre"),
  so that counterparts share their seat.
- Fields taking vocabulary keys are plain strings here and are checked against
  data/curated/vocab.yaml by the validator, so the vocabularies can grow without code changes.
- In CSV, list fields are "|"-separated and empty cells mean "none".
"""
from __future__ import annotations

import re
import typing
from fractions import Fraction
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
# Printed pages of the 1870 edition: "36", "36-37", "34;116"
PageRef = Annotated[str, StringConstraints(pattern=r"^\d{1,3}(?:-\d{1,3})?(?:;\s*\d{1,3}(?:-\d{1,3})?)*$")]
# The editor's entry number (1-2487), or "x-<page>-<n>" for an unnumbered item.
EntryNo = Annotated[str, StringConstraints(pattern=r"^(?:[1-9]\d{0,3}|x-\d{1,3}-\d{1,2})$")]
# "part" ("en partie"), a fraction ("1/2", "pour la moitié contre"), or "joint" for
# co-holders the book names together without shares.
Share = Annotated[str, StringConstraints(pattern=r"^(?:\d+/\d+|part|joint)$")]

LAST_ENTRY = 2487


def parse_pages(ref: str) -> list[int]:
    pages: list[int] = []
    for part in re.split(r";\s*", ref):
        a, _, b = part.partition("-")
        pages.extend(range(int(a), int(b or a) + 1))
    return pages


def share_value(share: str | None) -> Fraction | None:
    """Numeric share, or None for "part"/"joint"/unspecified."""
    if not share or share in ("part", "joint"):
        return None
    num, den = share.split("/")
    return Fraction(int(num), int(den))


def entry_number(no: str) -> int | None:
    """The numeric value of an entry number, None for unnumbered items."""
    return int(no) if no.isdigit() else None


class CsvRow(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Vocabulary each field must come from (checked by the validator); list fields are
    # checked item by item.
    vocab_fields: ClassVar[dict[str, str]] = {}

    @classmethod
    def columns(cls) -> list[str]:
        """CSV column order: the row's own fields first, provenance last."""
        tail = ["source_page", "confidence", "notes"]
        own = [f for f in cls.model_fields if f not in tail]
        return own + [f for f in tail if f in cls.model_fields]

    @classmethod
    def list_fields(cls) -> set[str]:
        hints = typing.get_type_hints(cls, include_extras=True)
        return {name for name in cls.model_fields if typing.get_origin(hints[name]) is list}

    @model_validator(mode="before")
    @classmethod
    def _from_csv(cls, data):
        if not isinstance(data, dict):
            return data
        lists = cls.list_fields()
        out = {}
        for key, value in data.items():
            if isinstance(value, str):
                value = value.strip()
                if key in lists:
                    value = [v.strip() for v in value.split("|") if v.strip()]
                elif value == "":
                    value = None
            if value is None and key in lists:
                value = []
            if value is not None:  # empty cell: let the field default apply
                out[key] = value
        return out


class Provenance(CsvRow):
    source_page: PageRef | None = None
    confidence: str = "high"
    notes: str | None = None


class Entry(Provenance):
    """One numbered item of the book, as printed (OCR-corrected)."""
    table: ClassVar[str] = "entries"
    vocab_fields: ClassVar[dict[str, str]] = {
        "descriptors": "place_types", "section": "sections", "series": "series",
        "order": "religious_orders", "confidence": "confidence",
    }

    no: EntryNo
    text: str
    name: str
    descriptors: list[str] = Field(default_factory=list)
    district_id: Slug | None = None   # the administrative division it stands under
    realm_id: Slug | None = None      # the feudal realm it stands under, if any
    section: str | None = None        # domain, fief, clergy, safeguard, other
    holder_id: list[Slug] = Field(default_factory=list)
    share: Share | None = None
    share_with: list[Slug] = Field(default_factory=list)
    series: str = "main"              # "main" for the Dénombrement, else the thematic list
    order: str | None = None          # religious order, for abbeys, priories, convents
    place_id: Slug | None = None


class Place(Provenance):
    table: ClassVar[str] = "places"
    vocab_fields: ClassVar[dict[str, str]] = {"confidence": "confidence", "counterpart_basis": "counterpart_bases"}
    # place_type is checked against place_types (settlements) or territory_types (territories).

    id: Slug
    kind: Literal["settlement", "territory"]
    name_fr: str
    name_de: str | None = None
    name_en: str | None = None
    variants: list[str] = Field(default_factory=list)
    place_type: str
    lat: Annotated[float, Field(ge=-90, le=90)] | None = None
    lon: Annotated[float, Field(ge=-180, le=180)] | None = None
    wikidata_id: Annotated[str, StringConstraints(pattern=r"^Q\d+$")] | None = None
    geonames_id: int | None = None
    modern_country: Literal["FR", "DE", "LU"] | None = None
    # The editor's identification in the index, as written in 1870.
    index_kind: str | None = None
    index_commune: str | None = None
    index_canton: str | None = None
    index_dept: str | None = None
    lost: bool = False                # no longer exists, or could not be identified
    # Territories only.
    hierarchy: Literal["admin", "feudal"] | None = None
    holder_id: list[Slug] = Field(default_factory=list)  # who holds a feudal realm (co-holders together)
    counterpart_id: Slug | None = None
    counterpart_basis: str | None = None  # heading, slot, alix_list, rule

    @model_validator(mode="after")
    def _check_kind(self):
        if self.kind == "settlement":
            for fld in ("hierarchy", "holder_id", "counterpart_id", "counterpart_basis"):
                if getattr(self, fld):
                    raise ValueError(f"{fld} is for territories only")
        return self


class Membership(Provenance):
    table: ClassVar[str] = "memberships"
    vocab_fields: ClassVar[dict[str, str]] = {"relation": "relations", "confidence": "confidence"}

    child_id: Slug
    parent_id: Slug
    relation: str                     # admin, feudal, ressort
    share: Share | None = None


class Entity(Provenance):
    table: ClassVar[str] = "entities"
    vocab_fields: ClassVar[dict[str, str]] = {"entity_type": "entity_types", "confidence": "confidence"}

    id: Slug
    name_en: str
    name_fr: str
    name_de: str
    entity_type: str
    color: Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")] | None = None


class Holding(Provenance):
    """Tenure of a place: generated from `entries` (Stage 4)."""
    table: ClassVar[str] = "holdings"
    vocab_fields: ClassVar[dict[str, str]] = {"tenure": "tenures", "confidence": "confidence"}

    place_id: Slug
    tenure: str                       # domain, fief, clergy, safeguard
    holder_id: Slug | None = None     # None: a fief or church land whose holder the book doesn't name
    share: Share | None = None
    share_with: list[Slug] = Field(default_factory=list)
    via_entry: list[EntryNo] = Field(default_factory=list)


class Feature(Provenance):
    """A thematic item without a number: mine, chaume (summer pasture), river."""
    table: ClassVar[str] = "features"
    vocab_fields: ClassVar[dict[str, str]] = {"theme": "feature_themes", "confidence": "confidence"}

    id: Slug
    theme: str
    name: str
    place_id: Slug | None = None
    attrs: str | None = None          # "metals=argent|cuivre", "gistes=2", the places along a river


TABLES: list[type[CsvRow]] = [Entry, Place, Membership, Entity, Holding, Feature]
