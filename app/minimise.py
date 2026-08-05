"""Delta debugging (ddmin) over a suite's check list and over a failing cart.

Two questions the detection matrix cannot answer:

1. **Which checks are load-bearing?** A suite of 24 checks that keeps its entire
   recall with 9 of them is carrying 15 checks of pure maintenance cost. The
   matrix shows what a suite catches, never what it would still catch after you
   deleted half of it.
2. **What is the smallest input that exposes a defect?** A three-line cart that
   reproduces a rounding bug is a bug report. A one-line cart is a test case.

Both use Zeller's ddmin, which returns a *1-minimal* result: removing any single
remaining element loses the property. It is not guaranteed globally minimal -
finding the true minimum here is set cover, which is NP-hard - and this module
never claims otherwise.

The check-set search runs against a cached outcome table rather than
re-executing. That is sound because checks share no state: each gets a fresh
`Ctx`, the targets are pure functions of their arguments, and the runner reseeds
the generator per execution from `(seed, build, repeat, check id)`. So one
execution per (check, build) is a complete oracle, and a fixed seed makes even
the nondeterministic defect's row of the table reproducible.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

from .defects import DEFECTS
from .runner import CLEAN, DEFAULT_SEED, execute_check
from .suites import BY_ID as SUITE_BY_ID
from .targets.checkout import price_cart


def ddmin(items: Sequence[Any], holds: Callable[[list], bool]) -> list:
    """Smallest 1-minimal subsequence of `items` for which `holds` is still true.

    `holds` must be true for the whole sequence; a predicate that is already
    false has nothing to minimise and is a caller error, not an empty answer.
    """
    items = list(items)
    if not holds(items):
        raise ValueError("ddmin requires the full sequence to satisfy the predicate")

    n = 2
    while len(items) >= 2:
        size = max(1, len(items) // n)
        starts = range(0, len(items), size)
        chunks = [items[i:i + size] for i in starts]
        complements = [items[:i] + items[i + size:] for i in starts]

        for chunk in chunks:  # can the whole property survive inside one chunk?
            if holds(chunk):
                items, n = chunk, 2
                break
        else:
            for rest in complements:  # otherwise, can one chunk be dropped?
                if rest and holds(rest):
                    items, n = rest, max(n - 1, 2)
                    break
            else:
                if n >= len(items):
                    break
                n = min(n * 2, len(items))
    return items


# ------------------------------------------------------- check-set searches ---

def outcome_table(
    suite_id: str, defect_ids: Iterable[str], seed: int = DEFAULT_SEED
) -> dict[tuple[str, str], bool]:
    """`(check id, build) -> passed` for the clean build plus one build per defect."""
    checks = SUITE_BY_ID[suite_id].checks
    builds = [CLEAN, *defect_ids]
    return {
        (chk.id, build): execute_check(
            chk, set() if build == CLEAN else {build}, seed, build, 0
        ).passed
        for build in builds
        for chk in checks
    }


def detects(table: dict, check_ids: Iterable[str], defect_id: str) -> bool:
    """The benchmark's detection rule, read off the table: fail on the defect
    build while passing on the clean one."""
    return any(
        table[(cid, CLEAN)] and not table[(cid, defect_id)] for cid in check_ids
    )


def detected_set(table: dict, check_ids: Iterable[str], defect_ids: Iterable[str]) -> frozenset:
    check_ids = list(check_ids)
    return frozenset(d for d in defect_ids if detects(table, check_ids, d))


def minimal_detecting_subset(
    suite_id: str, defect_id: str, seed: int = DEFAULT_SEED
) -> list[str]:
    """Smallest set of this suite's checks that still detects one defect.

    Returns `[]` when the suite never detected it - there is nothing to minimise.
    """
    check_ids = [c.id for c in SUITE_BY_ID[suite_id].checks]
    table = outcome_table(suite_id, [defect_id], seed)
    if not detects(table, check_ids, defect_id):
        return []
    return ddmin(check_ids, lambda subset: detects(table, subset, defect_id))


def minimal_recall_subset(
    suite_id: str, defect_ids: Iterable[str], seed: int = DEFAULT_SEED
) -> list[str]:
    """Smallest set of this suite's checks that detects exactly the same defects
    as the whole suite. Deleting the rest would cost the suite no recall."""
    defect_ids = list(defect_ids)
    check_ids = [c.id for c in SUITE_BY_ID[suite_id].checks]
    table = outcome_table(suite_id, defect_ids, seed)
    target = detected_set(table, check_ids, defect_ids)
    if not target:
        return []
    return ddmin(check_ids, lambda s: detected_set(table, s, defect_ids) == target)


def redundancy(
    suite_id: str, defect_ids: Iterable[str], seed: int = DEFAULT_SEED
) -> dict[str, Any]:
    """Per-suite redundancy report for the suite page. Builds the outcome table
    once and runs the whole search against it, so a page load costs one pass."""
    defect_ids = list(defect_ids)
    check_ids = [c.id for c in SUITE_BY_ID[suite_id].checks]
    table = outcome_table(suite_id, defect_ids, seed)
    target = detected_set(table, check_ids, defect_ids)
    keep = (
        ddmin(check_ids, lambda s: detected_set(table, s, defect_ids) == target)
        if target
        else []
    )
    return {
        "suite": suite_id,
        "n_checks": len(check_ids),
        "minimal": len(keep),
        "removable": len(check_ids) - len(keep),
        "keep": keep,
        "detected": len(target),
    }


# ------------------------------------------------------------ input search ---

def _total_or_error(cart: list[dict], active: set[str], promo: str | None) -> str:
    """Priced total as a string, or the rejection reason. A defect that removes a
    guard changes a cart from 'rejected' to 'priced', which is a difference too."""
    try:
        return str(price_cart(cart, active=active, promo=promo)["total"])
    except ValueError as exc:
        return f"rejected: {exc}"


def cart_exposes(cart: list[dict], defect_id: str, promo: str | None = None) -> bool:
    """True when this cart prices differently with the defect active."""
    if not cart:
        return False
    return _total_or_error(cart, set(), promo) != _total_or_error(cart, {defect_id}, promo)


def minimise_cart(
    cart: Sequence[dict], defect_id: str, promo: str | None = None
) -> list[dict]:
    """Smallest sub-cart that still prices differently with the defect active.

    Line-level only: it drops whole lines, it does not shrink a quantity or a
    unit price. Shrinking the values inside a line needs a different search and
    a per-field notion of "smaller"; this is the version that pays for itself.
    """
    cart = list(cart)
    if not cart_exposes(cart, defect_id, promo):
        raise ValueError(f"this cart does not expose {defect_id}; nothing to minimise")
    return ddmin(cart, lambda lines: cart_exposes(lines, defect_id, promo))


def demo() -> None:
    """Runnable self-check: python -m app.minimise"""
    cart = [
        {"sku": "PAD", "qty": 1, "unit_price": "2.00"},
        {"sku": "TIER", "qty": 3, "unit_price": "10.00"},  # exactly the tier boundary
        {"sku": "PAD2", "qty": 1, "unit_price": "5.00"},
    ]
    smallest = minimise_cart(cart, "CHK-002")
    assert [line["sku"] for line in smallest] == ["TIER"], smallest
    assert cart_exposes(smallest, "CHK-002")

    one = minimal_detecting_subset("expert", "CHK-004")
    assert len(one) == 1, one

    report = redundancy("expert", [d.id for d in DEFECTS])
    assert report["minimal"] <= report["n_checks"]
    print(f"cart minimised 3 -> {len(smallest)} line(s) for CHK-002")
    print(f"CHK-004 detected by a single check: {one[0]}")
    print(f"expert suite: {report['minimal']} of {report['n_checks']} checks carry all its recall")


if __name__ == "__main__":
    demo()
