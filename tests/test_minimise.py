"""Delta-debugging tests: the algorithm itself, then both searches it drives."""

import pytest

from app.defects import DEFECTS
from app.minimise import (
    cart_exposes,
    ddmin,
    detects,
    minimal_detecting_subset,
    minimal_recall_subset,
    minimise_cart,
    outcome_table,
    redundancy,
)

ALL_DEFECTS = [d.id for d in DEFECTS]


# --------------------------------------------------------------- algorithm ---

def test_ddmin_strips_everything_the_property_does_not_need():
    items = list(range(1, 9))
    result = ddmin(items, lambda s: 3 in s and 7 in s)
    assert result == [3, 7]


def test_ddmin_keeps_duplicates_apart_by_position():
    # Two identical elements must not both vanish when only one is required.
    result = ddmin(["a", "x", "a"], lambda s: s.count("a") >= 2)
    assert result == ["a", "a"]


def test_ddmin_result_is_one_minimal():
    items = list(range(12))
    needed = {2, 5, 9}
    result = ddmin(items, lambda s: needed <= set(s))
    assert set(result) == needed
    for element in result:  # removing any single element must lose the property
        assert not needed <= set(r for r in result if r != element)


def test_ddmin_refuses_a_predicate_that_is_already_false():
    with pytest.raises(ValueError, match="full sequence"):
        ddmin([1, 2, 3], lambda s: False)


# ------------------------------------------------------- minimal check sets ---

def test_chk_004_is_detected_by_a_single_expert_check():
    """BUG-9.1: the minimiser reduces the expert suite to one check for CHK-004."""
    keep = minimal_detecting_subset("expert", "CHK-004")
    assert len(keep) == 1
    # and prove the subset still detects it, rather than trusting the search
    table = outcome_table("expert", ["CHK-004"])
    assert detects(table, keep, "CHK-004")


def test_minimal_subset_is_empty_when_the_suite_never_caught_it():
    assert minimal_detecting_subset("expert", "CHK-003") == []
    assert minimal_detecting_subset("checklist", "AUT-001") == []


def test_minimal_recall_subset_loses_no_detection():
    keep = minimal_recall_subset("expert", ALL_DEFECTS)
    table = outcome_table("expert", ALL_DEFECTS)
    every_check = [c for (c, _b) in table if _b == "clean"]
    full = {d for d in ALL_DEFECTS if detects(table, every_check, d)}
    kept = {d for d in ALL_DEFECTS if detects(table, keep, d)}
    assert kept == full
    assert 0 < len(keep) <= len(every_check)


def test_minimal_recall_subset_is_one_minimal():
    keep = minimal_recall_subset("expert", ALL_DEFECTS)
    table = outcome_table("expert", ALL_DEFECTS)
    full = {d for d in ALL_DEFECTS if detects(table, keep, d)}
    for check_id in keep:
        thinner = [c for c in keep if c != check_id]
        assert {d for d in ALL_DEFECTS if detects(table, thinner, d)} != full


def test_redundancy_report_adds_up():
    report = redundancy("expert", ALL_DEFECTS)
    assert report["minimal"] + report["removable"] == report["n_checks"]
    assert report["detected"] == 16  # the expert suite's recall in the seeded run


def test_a_suite_that_detects_nothing_has_no_minimal_subset():
    # checklist against a defect it misses: nothing to keep, nothing removable
    keep = minimal_recall_subset("checklist", ["CHK-003"])
    assert keep == []


# ------------------------------------------------------- minimal cart input ---

THREE_LINE_CART = [
    {"sku": "PAD-A", "qty": 1, "unit_price": "2.00"},
    {"sku": "TIER", "qty": 3, "unit_price": "10.00"},  # exactly the tier boundary
    {"sku": "PAD-B", "qty": 1, "unit_price": "5.00"},
]


def test_minimise_cart_reduces_three_lines_to_the_one_that_matters():
    """BUG-9.3: only the boundary line is needed to expose CHK-002."""
    assert cart_exposes(THREE_LINE_CART, "CHK-002")
    smallest = minimise_cart(THREE_LINE_CART, "CHK-002")
    assert [line["sku"] for line in smallest] == ["TIER"]
    assert cart_exposes(smallest, "CHK-002")


def test_minimised_cart_cannot_be_cut_further():
    smallest = minimise_cart(THREE_LINE_CART, "CHK-002")
    for line in smallest:
        assert not cart_exposes([l for l in smallest if l is not line], "CHK-002")


def test_minimise_cart_refuses_a_cart_that_does_not_expose_the_defect():
    innocent = [{"sku": "PAD-A", "qty": 1, "unit_price": "2.00"}]
    assert not cart_exposes(innocent, "CHK-002")
    with pytest.raises(ValueError, match="does not expose"):
        minimise_cart(innocent, "CHK-002")


def test_minimise_cart_handles_a_defect_that_removes_a_guard():
    # CHK-006 drops the positive-quantity guard: clean rejects, defective prices.
    cart = [
        {"sku": "OK", "qty": 2, "unit_price": "4.00"},
        {"sku": "CREDIT", "qty": -1, "unit_price": "9.00"},
    ]
    smallest = minimise_cart(cart, "CHK-006")
    assert [line["sku"] for line in smallest] == ["CREDIT"]
