"""Clean-build behaviour of the ledger target."""

import pytest

from app.suites._kit import seeded_ledger
from app.targets import ledger

CLEAN: set[str] = set()


def balanced(key, amount=2500, tenant="acme", currency="EUR"):
    return {
        "idempotency_key": key,
        "tenant": tenant,
        "currency": currency,
        "legs": [{"account": "cash", "amount_cents": amount},
                 {"account": "revenue", "amount_cents": -amount}],
    }


def test_posting_a_balanced_entry_stores_it():
    store = ledger.new_store()
    out = ledger.post_entry(store, balanced("k1"), CLEAN)
    assert out["duplicate"] is False
    assert len(store["entries"]) == 1
    assert out["entry"]["id"] == 1


def test_replaying_an_idempotency_key_posts_once():
    store = ledger.new_store()
    ledger.post_entry(store, balanced("k1"), CLEAN)
    second = ledger.post_entry(store, balanced("k1"), CLEAN)
    assert second["duplicate"] is True
    assert len(store["entries"]) == 1
    assert ledger.balance_of(store, "cash", "EUR", CLEAN) == 2500


def test_distinct_keys_both_post():
    store = ledger.new_store()
    ledger.post_entry(store, balanced("k1"), CLEAN)
    ledger.post_entry(store, balanced("k2"), CLEAN)
    assert len(store["entries"]) == 2


@pytest.mark.parametrize("debit,credit", [(400, -300), (40000, -30000), (1, 0)])
def test_unbalanced_entries_are_refused_at_every_size(debit, credit):
    store = ledger.new_store()
    with pytest.raises(ledger.LedgerError):
        ledger.post_entry(store, {
            "idempotency_key": "bad", "currency": "EUR",
            "legs": [{"account": "cash", "amount_cents": debit},
                     {"account": "revenue", "amount_cents": credit}],
        }, CLEAN)
    assert store["entries"] == []


def test_entry_without_currency_is_refused():
    store = ledger.new_store()
    with pytest.raises(ledger.LedgerError):
        ledger.post_entry(store, {"idempotency_key": "x", "legs": [{"account": "a", "amount_cents": 0}]}, CLEAN)


def test_entry_without_legs_is_refused():
    store = ledger.new_store()
    with pytest.raises(ledger.LedgerError):
        ledger.post_entry(store, {"idempotency_key": "x", "currency": "EUR", "legs": []}, CLEAN)


def test_adjacent_pages_are_disjoint_and_contiguous():
    store = seeded_ledger(CLEAN)
    p1 = [r["id"] for r in ledger.list_entries(store, page=1, per_page=5, active=CLEAN)["items"]]
    p2 = [r["id"] for r in ledger.list_entries(store, page=2, per_page=5, active=CLEAN)["items"]]
    assert p1 == [1, 2, 3, 4, 5]
    assert p2 == [6, 7, 8, 9, 10]
    assert not set(p1) & set(p2)


def test_paging_covers_every_row_exactly_once():
    store = seeded_ledger(CLEAN)
    seen = []
    for page in range(1, 4):
        seen += [r["id"] for r in ledger.list_entries(store, page=page, per_page=5, active=CLEAN)["items"]]
    assert sorted(seen) == list(range(1, 13))
    assert len(seen) == len(set(seen))


def test_listing_reports_page_count():
    store = seeded_ledger(CLEAN)
    page = ledger.list_entries(store, page=1, per_page=5, active=CLEAN)
    assert page["total"] == 12
    assert page["pages"] == 3


def test_unfiltered_listing_is_scoped_to_the_tenant():
    store = seeded_ledger(CLEAN)
    page = ledger.list_entries(store, page=1, per_page=20, tenant="globex", active=CLEAN)
    assert page["total"] == 4
    assert all(r["tenant"] == "globex" for r in page["items"])


def test_filtered_listing_is_scoped_to_the_tenant():
    store = seeded_ledger(CLEAN)
    page = ledger.list_entries(store, page=1, per_page=20, tenant="globex", account="cash", active=CLEAN)
    assert all(r["tenant"] == "globex" for r in page["items"])


def test_balance_is_scoped_to_one_currency():
    store = seeded_ledger(CLEAN)
    assert ledger.balance_of(store, "cash", "EUR", CLEAN) == 54000
    assert ledger.balance_of(store, "cash", "USD", CLEAN) == 24000
    assert ledger.balance_of(store, "cash", None, CLEAN) == 78000


def test_double_entry_holds_across_the_whole_store():
    store = seeded_ledger(CLEAN)
    assert ledger.balance_of(store, "cash", None, CLEAN) + ledger.balance_of(store, "revenue", None, CLEAN) == 0
