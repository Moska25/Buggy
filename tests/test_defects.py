"""One test per seeded defect.

Each test asserts the clean behaviour and the defective behaviour of the same
call, which proves two things the benchmark depends on:

  1. every catalog entry is actually reachable and observable, so a "missed"
     cell in the matrix means the suite failed to probe it - not that the
     defect does nothing;
  2. each defect changes only what its catalog entry claims it changes.

If a defect ever stops being observable, the matrix silently starts lying. This
file is the guard against that.
"""

from decimal import Decimal as D

import pytest

from app.defects import BY_ID, DEFECTS
from app.suites._kit import forge_claims, seeded_ledger, tamper_tail
from app.targets import authn, ledger, rng
from app.targets.checkout import price_cart, tier_rate

CLEAN: set[str] = set()


def test_catalog_ids_are_unique_and_well_formed():
    ids = [d.id for d in DEFECTS]
    assert len(ids) == len(set(ids))
    assert len(DEFECTS) >= 14
    for d in DEFECTS:
        assert d.target in {"checkout", "authn", "ledger"}
        assert d.hint and d.description and d.title


def test_every_category_is_represented():
    from app.defects import CATEGORIES, category_counts

    counts = category_counts()
    assert all(counts[c] > 0 for c in CATEGORIES), counts


# ------------------------------------------------------------------ checkout ---

def test_chk_001_promo_discounts_shipping():
    cart = [{"sku": "A", "unit_price": "10.00", "qty": 2}]
    assert price_cart(cart, CLEAN, "SAVE10")["promo_discount"] == D("2.00")
    assert price_cart(cart, {"CHK-001"}, "SAVE10")["promo_discount"] == D("2.50")


def test_chk_002_tier_boundary_is_off_by_one():
    assert tier_rate(3, CLEAN) == D("0.05")
    assert tier_rate(3, {"CHK-002"}) == D("0")
    assert tier_rate(4, {"CHK-002"}) == D("0.05")   # only the boundary is wrong


def test_chk_003_rounding_differs_only_on_an_exact_tie():
    tie = [{"sku": "B", "unit_price": "1.41", "qty": 5}]
    assert price_cart(tie, CLEAN)["total"] == D("14.03")
    assert price_cart(tie, {"CHK-003"})["total"] == D("14.02")
    # ...and is invisible on a cart that does not land on a tie
    plain = [{"sku": "B", "unit_price": "2.00", "qty": 5}]
    assert price_cart(plain, CLEAN)["total"] == price_cart(plain, {"CHK-003"})["total"]


def test_chk_004_free_shipping_threshold_becomes_exclusive():
    at = [{"sku": "C", "unit_price": "25.00", "qty": 2}]          # goods exactly 50.00
    assert price_cart(at, CLEAN)["shipping"] == D("0.00")
    assert price_cart(at, {"CHK-004"})["shipping"] == D("4.99")
    above = [{"sku": "C", "unit_price": "25.01", "qty": 2}]
    assert price_cart(above, {"CHK-004"})["shipping"] == D("0.00")


def test_chk_005_vat_uses_the_pre_discount_subtotal():
    cart = [{"sku": "D", "unit_price": "14.00", "qty": 10}]
    assert price_cart(cart, CLEAN, "SAVE25")["vat"] == D("18.90")
    assert price_cart(cart, {"CHK-005"}, "SAVE25")["vat"] == D("25.20")


def test_chk_006_drops_quantity_validation():
    cart = [{"sku": "E", "unit_price": "5.00", "qty": -2}]
    with pytest.raises(ValueError):
        price_cart(cart, CLEAN)
    assert price_cart(cart, {"CHK-006"})["goods"] < 0   # a negative line becomes a credit


# --------------------------------------------------------------------- authn ---

def test_aut_001_accepts_expired_tokens_inside_the_grace_window():
    token = authn.issue_token("bob", iat=1000, ttl=100)
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=1101, active=CLEAN)
    assert authn.verify_token(token, now=1101, active={"AUT-001"})["sub"] == "bob"
    # far past expiry it still refuses, which is why a lazy expiry probe misses it
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=1101 + 3600, active={"AUT-001"})


def test_aut_002_truncates_the_signature_comparison():
    token = authn.issue_token("carol", iat=0, ttl=1000)
    tampered = tamper_tail(token)
    with pytest.raises(authn.AuthError):
        authn.verify_token(tampered, now=10, active=CLEAN)
    assert authn.verify_token(tampered, now=10, active={"AUT-002"})["sub"] == "carol"


def test_aut_003_substring_role_bypasses_the_scope_check():
    token = authn.issue_token("mallory", roles=["billing_admin"], scopes=[], iat=0, ttl=1000)
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=10, active=CLEAN, required_scope="payouts:write")
    assert authn.verify_token(token, now=10, active={"AUT-003"}, required_scope="payouts:write")


def test_aut_004_returns_none_instead_of_raising():
    with pytest.raises(authn.AuthError):
        authn.verify_token("not-a-token", now=10, active=CLEAN)
    assert authn.verify_token("not-a-token", now=10, active={"AUT-004"}) is None


def test_aut_005_revocation_matches_the_wrong_claim():
    token = authn.issue_token("frank", iat=0, ttl=1000, jti="tok-1")
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=10, active=CLEAN, revoked={"tok-1"})
    assert authn.verify_token(token, now=10, active={"AUT-005"}, revoked={"tok-1"})
    # it matches the subject instead, which is the tell
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=10, active={"AUT-005"}, revoked={"frank"})


def test_aut_006_is_intermittent_rather_than_constant():
    token = authn.issue_token("gina", iat=0, ttl=1000)
    forged = forge_claims(token, roles=["admin"])
    accepted = 0
    trials = 400
    for seed in range(trials):
        rng.reseed(seed)
        try:
            authn.verify_token(forged, now=10, active={"AUT-006"})
            accepted += 1
        except authn.AuthError:
            pass
    assert 0 < accepted < trials, "the defect must be intermittent, not always-on or always-off"
    assert 0.22 < accepted / trials < 0.38, f"expected roughly the configured 30% share, got {accepted / trials:.3f}"


def test_aut_006_is_reproducible_for_a_given_seed():
    token = authn.issue_token("gina", iat=0, ttl=1000)
    forged = forge_claims(token, roles=["admin"])

    def outcome(seed):
        rng.reseed(seed)
        try:
            authn.verify_token(forged, now=10, active={"AUT-006"})
            return True
        except authn.AuthError:
            return False

    assert [outcome(s) for s in range(30)] == [outcome(s) for s in range(30)]


# -------------------------------------------------------------------- ledger ---

def _entry(key="retry-1", amount=2500):
    return {
        "idempotency_key": key, "tenant": "acme", "currency": "EUR",
        "legs": [{"account": "cash", "amount_cents": amount},
                 {"account": "revenue", "amount_cents": -amount}],
    }


def test_led_001_retry_double_posts():
    clean_store = ledger.new_store()
    ledger.post_entry(clean_store, _entry(), CLEAN)
    ledger.post_entry(clean_store, _entry(), CLEAN)
    assert len(clean_store["entries"]) == 1

    bug_store = ledger.new_store()
    ledger.post_entry(bug_store, _entry(), {"LED-001"})
    second = ledger.post_entry(bug_store, _entry(), {"LED-001"})
    assert second["duplicate"] is False
    assert len(bug_store["entries"]) == 2
    assert ledger.balance_of(bug_store, "cash", "EUR", {"LED-001"}) == 5000


def test_led_002_skips_the_invariant_for_small_entries():
    small = {"idempotency_key": "s", "currency": "EUR",
             "legs": [{"account": "cash", "amount_cents": 400},
                      {"account": "revenue", "amount_cents": -300}]}
    with pytest.raises(ledger.LedgerError):
        ledger.post_entry(ledger.new_store(), small, CLEAN)

    store = ledger.new_store()
    ledger.post_entry(store, small, {"LED-002"})
    assert len(store["entries"]) == 1

    big = {"idempotency_key": "b", "currency": "EUR",
           "legs": [{"account": "cash", "amount_cents": 40000},
                    {"account": "revenue", "amount_cents": -30000}]}
    with pytest.raises(ledger.LedgerError):
        ledger.post_entry(ledger.new_store(), big, {"LED-002"})


def test_led_003_repeats_a_row_at_the_page_edge():
    store = seeded_ledger(CLEAN)
    clean_p2 = [r["id"] for r in ledger.list_entries(store, page=2, per_page=5, active=CLEAN)["items"]]
    bug_p2 = [r["id"] for r in ledger.list_entries(store, page=2, per_page=5, active={"LED-003"})["items"]]
    assert clean_p2 == [6, 7, 8, 9, 10]
    assert bug_p2 == [5, 6, 7, 8, 9]        # row 5 is served on both pages
    bug_p1 = [r["id"] for r in ledger.list_entries(store, page=1, per_page=5, active={"LED-003"})["items"]]
    assert set(bug_p1) & set(bug_p2) == {5}


def test_led_004_sums_across_currencies():
    store = seeded_ledger(CLEAN)
    assert ledger.balance_of(store, "cash", "EUR", CLEAN) == 54000
    assert ledger.balance_of(store, "cash", "EUR", {"LED-004"}) == 78000


def test_led_005_leaks_other_tenants_on_the_unfiltered_listing():
    store = seeded_ledger(CLEAN)
    clean_page = ledger.list_entries(store, page=1, per_page=20, tenant="globex", active=CLEAN)
    bug_page = ledger.list_entries(store, page=1, per_page=20, tenant="globex", active={"LED-005"})
    assert clean_page["total"] == 4
    assert bug_page["total"] == 12
    assert any(r["tenant"] != "globex" for r in bug_page["items"])
    # with an account filter the tenant filter still applies
    filtered = ledger.list_entries(store, page=1, per_page=20, tenant="globex",
                                   account="cash", active={"LED-005"})
    assert filtered["total"] == 4


@pytest.mark.parametrize("defect", [d.id for d in DEFECTS])
def test_every_defect_has_a_catalog_entry_and_a_hint(defect):
    d = BY_ID[defect]
    assert len(d.hint) > 40, "the hint must describe the probe, not just name it"
    assert d.severity in {"blocker", "major", "minor"}
