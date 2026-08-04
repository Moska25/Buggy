"""Spec checklist suite - the control.

One check per spec bullet, all happy path, all loose assertions. Nothing here
is dishonest or incompetent; it is simply what a suite looks like when it was
written to cover the requirements list rather than to break the code. It has
coverage, it has green ticks, and it is nearly blind.

This is the baseline the whole benchmark exists to contrast against.
"""

from __future__ import annotations

from ..targets import authn, ledger
from ..targets.checkout import price_cart
from . import Ctx, check
from ._kit import seeded_ledger

S = "checklist"


@check(suite=S, target="checkout", id="LST-CHK-01",
       title="A cart can be priced",
       intent="Spec bullet: 'the checkout returns a priced cart'.")
def _(ctx: Ctx) -> None:
    ctx.step("price a two-line cart")
    r = price_cart([
        {"sku": "A", "unit_price": "12.00", "qty": 2},
        {"sku": "B", "unit_price": "4.50", "qty": 1},
    ], ctx.active)
    ctx.expect(r["total"] > 0, f"a priced cart has a positive total, got {r['total']}")
    ctx.expect(len(r["lines"]) == 2, f"two lines in, two lines out, got {len(r['lines'])}")


@check(suite=S, target="checkout", id="LST-CHK-02",
       title="A promo code reduces the total",
       intent="Spec bullet: 'promo codes take a percentage off'.")
def _(ctx: Ctx) -> None:
    cart = [{"sku": "C", "unit_price": "20.00", "qty": 2}]
    ctx.step("price with and without SAVE10")
    plain = price_cart(cart, ctx.active)
    promo = price_cart(cart, ctx.active, "SAVE10")
    ctx.expect(promo["total"] < plain["total"], f"promo must reduce the total: {promo['total']} vs {plain['total']}")


@check(suite=S, target="checkout", id="LST-CHK-03",
       title="Large orders ship free",
       intent="Spec bullet: 'delivery is free over 50.00'.")
def _(ctx: Ctx) -> None:
    ctx.step("price a 120.00 order")
    r = price_cart([{"sku": "D", "unit_price": "60.00", "qty": 2}], ctx.active)
    ctx.expect(r["shipping"] == 0, f"free shipping on a large order, got {r['shipping']}")


@check(suite=S, target="checkout", id="LST-CHK-04",
       title="Bulk quantities attract a discount",
       intent="Spec bullet: 'buying more is cheaper per unit'.")
def _(ctx: Ctx) -> None:
    ctx.step("price 10 units and confirm a tier discount was applied")
    r = price_cart([{"sku": "E", "unit_price": "3.00", "qty": 10}], ctx.active)
    ctx.expect(r["lines"][0]["tier_discount"] > 0, f"a bulk line is discounted, got {r['lines'][0]['tier_discount']}")


@check(suite=S, target="checkout", id="LST-CHK-05",
       title="VAT is lower on a discounted order",
       intent="Spec bullet: 'tax is charged on what the customer pays'.")
def _(ctx: Ctx) -> None:
    cart = [{"sku": "F", "unit_price": "14.00", "qty": 10}]
    ctx.step("compare VAT with and without SAVE25")
    plain = price_cart(cart, ctx.active)
    promo = price_cart(cart, ctx.active, "SAVE25")
    ctx.expect(promo["vat"] < plain["vat"], f"VAT must follow the discount: {promo['vat']} vs {plain['vat']}")


@check(suite=S, target="authn", id="LST-AUT-01",
       title="A valid token verifies",
       intent="Spec bullet: 'tokens can be issued and verified'.")
def _(ctx: Ctx) -> None:
    ctx.step("issue and immediately verify")
    token = authn.issue_token("alice", roles=["user"], scopes=["read"], iat=1000, ttl=3600)
    claims = authn.verify_token(token, now=1500, active=ctx.active)
    ctx.expect(bool(claims), "a fresh token verifies")


@check(suite=S, target="authn", id="LST-AUT-02",
       title="An expired token is rejected",
       intent="Spec bullet: 'tokens expire'.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("bob", scopes=["read"], iat=1000, ttl=100)
    ctx.step("verify long after expiry (t = exp + 10000)")
    try:
        authn.verify_token(token, now=11100, active=ctx.active)
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "an expired token is refused")


@check(suite=S, target="authn", id="LST-AUT-03",
       title="A missing scope is refused",
       intent="Spec bullet: 'scopes gate access'.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("carol", roles=["user"], scopes=["read"], iat=0, ttl=1000)
    ctx.step("demand a scope the token does not carry")
    try:
        authn.verify_token(token, now=10, active=ctx.active, required_scope="write")
        refused = False
    except authn.AuthError:
        refused = True
    ctx.expect(refused, "a token without the scope is refused")


@check(suite=S, target="ledger", id="LST-LED-01",
       title="A posted entry appears in the listing",
       intent="Spec bullet: 'entries are stored and can be listed'.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    ctx.step("post one balanced entry and list it back")
    ledger.post_entry(store, {
        "idempotency_key": "k-1", "currency": "EUR",
        "legs": [{"account": "cash", "amount_cents": 1500}, {"account": "revenue", "amount_cents": -1500}],
    }, ctx.active)
    page = ledger.list_entries(store, page=1, per_page=5, active=ctx.active)
    ctx.expect(page["total"] == 1, f"one entry stored, listing reported {page['total']}")


@check(suite=S, target="ledger", id="LST-LED-02",
       title="Reposting the same key is reported as a duplicate",
       intent="Spec bullet: 'posts are idempotent'.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    entry = {
        "idempotency_key": "k-2", "currency": "EUR",
        "legs": [{"account": "cash", "amount_cents": 900}, {"account": "revenue", "amount_cents": -900}],
    }
    ctx.step("post the same entry twice")
    ledger.post_entry(store, entry, ctx.active)
    again = ledger.post_entry(store, entry, ctx.active)
    ctx.expect(again["duplicate"] is True, "the second post is flagged as a duplicate")


@check(suite=S, target="ledger", id="LST-LED-03",
       title="A page never exceeds its page size",
       intent="Spec bullet: 'listings are paginated'.")
def _(ctx: Ctx) -> None:
    store = seeded_ledger(ctx.active)
    ctx.step("read page 2 at per_page=5")
    page = ledger.list_entries(store, page=2, per_page=5, active=ctx.active)
    ctx.expect(len(page["items"]) <= 5, f"at most 5 rows per page, got {len(page['items'])}")
