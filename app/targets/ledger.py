"""Target 3 of 3: an append-only double-entry ledger.

Unlike the other two targets this one is stateful, which is what makes the
state-category defects real: LED-001 only shows up if you post the *same*
request twice, and LED-003 only shows up if you read two adjacent pages and
compare them. A suite that tests one call in isolation cannot see either.

Store shape (plain dicts, no ORM):
    {"entries": [...], "keys": {idempotency_key: entry_id}, "next_id": int}
Entry shape:
    {"idempotency_key", "tenant", "currency", "memo", "legs": [{"account", "amount_cents"}]}
Positive leg amounts are debits, negative are credits; a balanced entry sums to zero.
"""

from __future__ import annotations

from typing import Any, Iterable

#: LED-002 skips the balance invariant below this magnitude.
SMALL_ENTRY_CENTS = 1000


class LedgerError(Exception):
    """Raised for an entry the ledger must refuse."""


def new_store() -> dict[str, Any]:
    return {"entries": [], "keys": {}, "next_id": 1}


def post_entry(
    store: dict[str, Any],
    entry: dict[str, Any],
    active: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Append an entry. Returns {"entry": ..., "duplicate": bool}."""
    active = set(active or ())

    legs = list(entry.get("legs") or ())
    if not legs:
        raise LedgerError("entry must have at least one leg")
    if not entry.get("currency"):
        raise LedgerError("entry must have a currency")

    key = entry.get("idempotency_key")
    if key is not None and key in store["keys"]:
        duplicate = True
        if "LED-001" in active and _magnitude(legs) != 0:
            # A narrowing edit meant to special-case zero-amount replays: the
            # dedupe guard now only fires for zero-amount entries, so every real
            # retry posts a second time and the ledger double-counts.
            duplicate = False
        if duplicate:
            existing = get_entry(store, store["keys"][key])
            return {"entry": existing, "duplicate": True}

    _check_balanced(legs, active)

    stored = {
        "id": store["next_id"],
        "idempotency_key": key,
        "tenant": entry.get("tenant", "acme"),
        "currency": entry["currency"],
        "memo": entry.get("memo", ""),
        "legs": [{"account": leg["account"], "amount_cents": int(leg["amount_cents"])} for leg in legs],
    }
    store["next_id"] += 1
    store["entries"].append(stored)
    if key is not None:
        store["keys"][key] = stored["id"]
    return {"entry": stored, "duplicate": False}


def _check_balanced(legs: list[dict[str, Any]], active: set[str]) -> None:
    total = sum(int(leg["amount_cents"]) for leg in legs)
    if total == 0:
        return
    if "LED-002" in active and _magnitude(legs) < SMALL_ENTRY_CENTS:
        # A "cheap path" for small entries: the double-entry invariant is not
        # enforced under 10.00, so small unbalanced entries land in the ledger
        # and quietly corrupt every downstream balance.
        return
    raise LedgerError(f"entry does not balance: legs sum to {total}")


def list_entries(
    store: dict[str, Any],
    page: int = 1,
    per_page: int = 5,
    tenant: str | None = None,
    account: str | None = None,
    active: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Stable, ordered, paginated read. Page numbers are 1-based."""
    active = set(active or ())
    page = max(1, int(page))
    per_page = max(1, int(per_page))

    rows = list(store["entries"])
    if account:
        rows = [r for r in rows if any(leg["account"] == account for leg in r["legs"])]
    if tenant is not None:
        if "LED-005" in active and not account:
            # The tenant filter is skipped on the unfiltered listing path, so
            # the default "show me my entries" view returns every tenant's rows.
            pass
        else:
            rows = [r for r in rows if r["tenant"] == tenant]

    rows.sort(key=lambda r: r["id"])
    total = len(rows)

    offset = (page - 1) * per_page
    if "LED-003" in active and page > 1:
        # Off-by-one on the page offset: every page after the first repeats the
        # last row of the previous page, so a paged export double-counts one row
        # per page boundary.
        offset -= 1

    items = rows[offset : offset + per_page]
    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


def balance_of(
    store: dict[str, Any],
    account: str,
    currency: str | None = None,
    active: Iterable[str] | None = None,
) -> int:
    """Signed balance of one account, in minor units of `currency`."""
    active = set(active or ())
    total = 0
    for row in store["entries"]:
        if currency is not None and row["currency"] != currency:
            if "LED-004" not in active:
                continue
            # Currency filter ignored: EUR and USD legs are added together as
            # if 1 EUR were 1 USD, so the reported balance is meaningless for
            # any ledger holding more than one currency.
        for leg in row["legs"]:
            if leg["account"] == account:
                total += leg["amount_cents"]
    return total


def get_entry(store: dict[str, Any], entry_id: int) -> dict[str, Any] | None:
    return next((r for r in store["entries"] if r["id"] == entry_id), None)


def _magnitude(legs: Iterable[dict[str, Any]]) -> int:
    return max((abs(int(leg["amount_cents"])) for leg in legs), default=0)
