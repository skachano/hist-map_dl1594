"""The validator on the hand-checked sample (tests/fixtures/sample) and on broken copies of it."""
import copy
import json
from pathlib import Path

import pytest

from denombrement.data import schema, store, validate
from denombrement.data.models import Entry, Membership, Place

SAMPLE = Path(__file__).parent / "fixtures" / "sample"


@pytest.fixture(scope="module")
def sample() -> store.Dataset:
    return store.load(SAMPLE)


def levels(ds: store.Dataset) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"error": [], "warning": [], "info": []}
    for issue in validate.validate(ds):
        out[issue.level].append(issue.message)
    return out


def changed(ds: store.Dataset, table: str, match, **update) -> store.Dataset:
    """A copy of the dataset with the first matching row of `table` updated."""
    ds = copy.deepcopy(ds)
    rows = getattr(ds, table)
    for i, (line, row) in enumerate(rows):
        if match(row):
            rows[i] = (line, row.model_copy(update=update))
            return ds
    raise AssertionError("no row matched")


def added(ds: store.Dataset, table: str, row) -> store.Dataset:
    ds = copy.deepcopy(ds)
    getattr(ds, table).append((999, row))
    return ds


def test_sample_is_valid(sample):
    found = levels(sample)
    assert found["error"] == [] and found["warning"] == []
    assert any("differ" in m for m in found["info"])  # the abbey's villages are outside the lordship


def test_sample_coverage(sample):
    lines = validate.coverage(sample)
    assert "counterpart pairs: 2" in lines[1]


@pytest.mark.parametrize("update, message", [
    (dict(district_id="fief-keltern-ostern"), "is not an administrative territory"),
    (dict(realm_id="provostship-nancy"), "is not a feudal territory"),
    (dict(section=None), "needs its section"),
    (dict(district_id=None), "needs its district"),
    (dict(descriptors=["fortress"]), "is not in vocab.place_types"),
    (dict(holder_id=["nobody"]), "not found in entities"),
])
def test_entry_errors(sample, update, message):
    ds = changed(sample, "entries", lambda e: e.no == "1546", **update)
    assert any(message in m for m in levels(ds)["error"])


def test_entry_numbers(sample):
    ds = added(sample, "entries", Entry(no="1546", text="x", name="x", district_id="office-schaumburg",
                                        section="fief", source_page="89"))
    found = levels(ds)
    assert any("duplicate id '1546'" in m for m in found["error"])
    assert any("out of sequence" in m for m in found["warning"])
    ds = changed(sample, "entries", lambda e: e.no == "2281", no="2600")
    assert any("outside 1-2487" in m for m in levels(ds)["error"])


def test_entry_without_membership(sample):
    ds = changed(sample, "entries", lambda e: e.no == "2268", realm_id="lordship-hombourg-saint-avold")
    assert any("no feudal membership guessling" in m for m in levels(ds)["warning"])


@pytest.mark.parametrize("membership, message", [
    (Membership(child_id="nancy", parent_id="county-chaligny", relation="admin", source_page="35"),
     "an admin link joins administrative divisions"),
    (Membership(child_id="nancy", parent_id="provostship-nancy", relation="feudal", source_page="35"),
     "a feudal link joins feudal realms"),
    (Membership(child_id="provostship-nancy", parent_id="county-chaligny", relation="ressort", source_page="35"),
     "a ressort link goes from a feudal realm"),
    (Membership(child_id="nancy", parent_id="azelot", relation="admin", source_page="35"),
     "is not a territory"),
    (Membership(child_id="duchy-lorraine", parent_id="provostship-nancy", relation="admin", source_page="34"),
     "membership cycle"),
])
def test_membership_errors(sample, membership, message):
    assert any(message in m for m in levels(added(sample, "memberships", membership))["error"])


def test_ressort_of_a_paired_realm(sample):
    ds = added(sample, "memberships", Membership(child_id="lordship-hombourg-saint-avold",
                                                 parent_id="provostship-nancy", relation="ressort", source_page="114"))
    assert any("its ressort should be 'castellany-hombourg-saint-avold'" in m for m in levels(ds)["warning"])


def test_settlement_must_reach_the_duchy(sample):
    ds = added(sample, "places", Place(id="nowhere", kind="settlement", name_fr="Nulle part", place_type="village"))
    assert any("'nowhere' does not reach the duchy" in m for m in levels(ds)["error"])


@pytest.mark.parametrize("pid, update, message", [
    ("provostship-keltern-ostern", dict(counterpart_id="county-chaligny"), "does not point back"),
    ("provostship-keltern-ostern", dict(counterpart_basis=None), "counterpart_basis is required"),
    ("provostship-keltern-ostern", dict(holder_id=["duchy-lorraine"]), "an administrative division has no holder"),
    ("county-chaligny", dict(hierarchy="admin"), "a county is feudal"),
    ("county-chaligny", dict(place_type="castle"), "is not in vocab.territory_types"),
])
def test_place_errors(sample, pid, update, message):
    ds = changed(sample, "places", lambda p: p.id == pid, **update)
    assert any(message in m for m in levels(ds)["error"])


def test_counterparts_in_the_same_hierarchy(sample):
    ds = changed(sample, "places", lambda p: p.id == "fief-keltern-ostern", hierarchy="admin", place_type="provostship")
    assert any("must be a territory of the other hierarchy" in m for m in levels(ds)["error"])


def test_holdings(sample):
    ds = changed(sample, "holdings", lambda h: h.place_id == "nancy", holder_id="house-eberstein")
    assert any("the domain is the duke's" in m for m in levels(ds)["warning"])
    ds = changed(sample, "holdings", lambda h: h.place_id == "nancy", share="3/2")
    assert any("add up to 3/2" in m for m in levels(ds)["error"])


def test_vocab_needs_four_languages(sample):
    ds = copy.deepcopy(sample)
    del ds.vocab["tenures"]["fief"]["ja"]
    assert any("tenures.fief lacks labels: ['ja']" in m for m in levels(ds)["error"])


def test_schema_has_vocabulary_enums(sample):
    s = schema.table_schema(Entry, sample.vocab)
    assert "clergy" in s["properties"]["section"]["anyOf"][0]["enum"]
    assert "castle" in s["properties"]["descriptors"]["items"]["enum"]
    p = schema.table_schema(Place, sample.vocab)
    assert {"village", "provostship", "lordship"} <= set(p["properties"]["place_type"]["enum"])
    json.dumps(s)
