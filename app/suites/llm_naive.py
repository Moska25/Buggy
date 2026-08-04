"""LLM suite, spec-only condition - RECORDED FIXTURE.

Read this header before reading the checks.

This file is a committed fixture. It was authored once to represent the
spec-only condition - checks written from the prose specification, with no
access to the target source and no ability to execute anything - and then
checked in so the benchmark is reproducible and runs offline. Buggy does not
call a model at run time, requires no API key, and never regenerates a suite
live. Live generation is Phase 6 in TODO.md and is not built.

The characteristic failure mode of this condition is not laziness - the
coverage looks respectable - it is confident assertions about behaviour the
spec never actually promised. Two of the checks below (NAI-CHK-05, NAI-AUT-04)
assert wrong behaviour and therefore fail against the clean build. Those are
false positives, not detections, and the runner refuses to give them credit.
"""

from __future__ import annotations

from decimal import Decimal as D

from ..targets import authn, ledger
from ..targets.checkout import price_cart
from . import Ctx, check
from ._kit import forge_claims, seeded_ledger

S = "llm_naive"


@check(suite=S, target="checkout", id="NAI-CHK-01",
       title="A simple cart prices correctly",
       intent="Anchor the pipeline with a straightforward cart.")
def _(ctx: Ctx) -> None:
    ctx.step("price 5 x 2.00")
    r = price_cart([{"sku": "A", "unit_price": "2.00", "qty": 5}], ctx.active)
    ctx.expect(r["total"] == D("17.39"), f"expected 17.39, got {r['total']}")


@check(suite=S, target="checkout", id="NAI-CHK-02",
       title="A 10% promo takes 10% of the goods total",
       intent="The discount should be a percentage of the items, not of the order.")
def _(ctx: Ctx) -> None:
    ctx.step("price 2 x 10.00 with SAVE10")
    r = price_cart([{"sku": "B", "unit_price": "10.00", "qty": 2}], ctx.active, "SAVE10")
    ctx.expect(r["promo_discount"] == D("2.00"), f"expected a 2.00 discount, got {r['promo_discount']}")


@check(suite=S, target="checkout", id="NAI-CHK-03",
       title="Tax follows the discount",
       intent="A discounted order should be taxed on the discounted amount.")
def _(ctx: Ctx) -> None:
    cart = [{"sku": "C", "unit_price": "14.00", "qty": 10}]
    ctx.step("compare VAT with and without SAVE25")
    plain = price_cart(cart, ctx.active)
    promo = price_cart(cart, ctx.active, "SAVE25")
    ctx.expect(promo["vat"] < plain["vat"], f"VAT should drop: {promo['vat']} vs {plain['vat']}")


@check(suite=S, target="checkout", id="NAI-CHK-04",
       title="A zero quantity is rejected",
       intent="Input validation on the quantity field.")
def _(ctx: Ctx) -> None:
    ctx.step("price a line with qty 0")
    try:
        price_cart([{"sku": "D", "unit_price": "5.00", "qty": 0}], ctx.active)
        raised = False
    except ValueError:
        raised = True
    ctx.expect(raised, "qty 0 should raise ValueError")


@check(suite=S, target="checkout", id="NAI-CHK-05",
       title="A promo code discounts the final amount payable",
       intent="Reads the spec as 'take 10% off what the customer pays', i.e. after tax.")
def _(ctx: Ctx) -> None:
    # This check asserts behaviour the specification does not promise. The promo
    # is applied to goods before VAT, so this fails against the clean build and
    # is a false positive rather than a finding.
    cart = [{"sku": "E", "unit_price": "10.00", "qty": 2}]
    ctx.step("price with and without SAVE10 and compare the final totals")
    plain = price_cart(cart, ctx.active)
    promo = price_cart(cart, ctx.active, "SAVE10")
    expected = (plain["total"] * D("0.90")).quantize(D("0.01"))
    ctx.expect(promo["total"] == expected, f"expected 10% off the final total ({expected}), got {promo['total']}")


@check(suite=S, target="checkout", id="NAI-CHK-06",
       title="Bulk lines get a tier discount",
       intent="Quantity breaks should apply to a large line.")
def _(ctx: Ctx) -> None:
    ctx.step("price 10 x 3.00")
    r = price_cart([{"sku": "F", "unit_price": "3.00", "qty": 10}], ctx.active)
    ctx.expect(r["lines"][0]["tier_rate"] == D("0.10"), f"expected the 10% tier, got {r['lines'][0]['tier_rate']}")


@check(suite=S, target="checkout", id="NAI-CHK-07",
       title="Orders over the threshold ship free",
       intent="Delivery is free above the advertised amount.")
def _(ctx: Ctx) -> None:
    ctx.step("price a 130.00 order")
    r = price_cart([{"sku": "G", "unit_price": "65.00", "qty": 2}], ctx.active)
    ctx.expect(r["shipping"] == D("0.00"), f"expected free shipping, got {r['shipping']}")


@check(suite=S, target="checkout", id="NAI-CHK-08",
       title="Line totals equal unit price times quantity before discount",
       intent="Basic arithmetic on the line itself.")
def _(ctx: Ctx) -> None:
    ctx.step("price 4 x 7.25 and inspect the line")
    r = price_cart([{"sku": "H", "unit_price": "7.25", "qty": 4}], ctx.active)
    ctx.expect(r["lines"][0]["gross"] == D("29.00"), f"expected gross 29.00, got {r['lines'][0]['gross']}")


@check(suite=S, target="authn", id="NAI-AUT-01",
       title="Issued tokens verify",
       intent="The basic issue-then-verify path.")
def _(ctx: Ctx) -> None:
    ctx.step("issue for alice, verify inside the window")
    token = authn.issue_token("alice", roles=["user"], scopes=["read"], iat=1000, ttl=3600)
    claims = authn.verify_token(token, now=2000, active=ctx.active)
    ctx.expect(claims and claims["sub"] == "alice", f"expected alice's claims, got {claims}")


@check(suite=S, target="authn", id="NAI-AUT-02",
       title="A forged token is rejected",
       intent="Rewriting the claims to grant admin must not survive verification.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("bob", roles=["user"], scopes=["read"], iat=0, ttl=10000)
    forged = forge_claims(token, roles=["admin"], scopes=["read", "write", "admin"])
    ctx.step("verify the forged token once")
    try:
        authn.verify_token(forged, now=10, active=ctx.active, required_scope="admin")
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "a forged token should be rejected")


@check(suite=S, target="authn", id="NAI-AUT-03",
       title="Expired tokens stop working",
       intent="Tokens must not outlive their lifetime.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("carol", scopes=["read"], iat=1000, ttl=3600)
    ctx.step("verify a day after issue")
    try:
        authn.verify_token(token, now=1000 + 86400, active=ctx.active)
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "an expired token should be rejected")


@check(suite=S, target="authn", id="NAI-AUT-04",
       title="A token is dead the moment it reaches its expiry",
       intent="Reads 'expires at exp' as 'invalid at exp'.")
def _(ctx: Ctx) -> None:
    # This check asserts the exclusive reading of the expiry bound. The clean
    # implementation treats exp as the last valid second, so this fails against
    # the clean build: a false positive, not a finding.
    token = authn.issue_token("dave", scopes=["read"], iat=1000, ttl=100)
    ctx.step("verify at exactly exp = 1100")
    try:
        authn.verify_token(token, now=1100, active=ctx.active)
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "a token at exactly its expiry second should be rejected")


@check(suite=S, target="authn", id="NAI-AUT-05",
       title="A revoked token stops verifying",
       intent="Revocation must take effect immediately.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("erin", scopes=["read"], iat=0, ttl=10000, jti="tok-erin-9")
    ctx.step("revoke tok-erin-9, then verify")
    try:
        authn.verify_token(token, now=20, active=ctx.active, revoked={"tok-erin-9"})
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "a revoked token should be rejected")


@check(suite=S, target="ledger", id="NAI-LED-01",
       title="Retrying a post does not duplicate it",
       intent="The idempotency key should collapse a retry.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    entry = {
        "idempotency_key": "inv-7", "currency": "EUR",
        "legs": [{"account": "cash", "amount_cents": 5000}, {"account": "revenue", "amount_cents": -5000}],
    }
    ctx.step("post inv-7 twice")
    ledger.post_entry(store, entry, ctx.active)
    ledger.post_entry(store, entry, ctx.active)
    ctx.expect(len(store["entries"]) == 1, f"expected 1 stored entry, found {len(store['entries'])}")


@check(suite=S, target="ledger", id="NAI-LED-02",
       title="A tenant only sees its own entries",
       intent="Multi-tenant isolation on the listing endpoint.")
def _(ctx: Ctx) -> None:
    store = seeded_ledger(ctx.active)
    ctx.step("list for tenant acme")
    page = ledger.list_entries(store, page=1, per_page=20, tenant="acme", active=ctx.active)
    leaked = [r["id"] for r in page["items"] if r["tenant"] != "acme"]
    ctx.expect(not leaked, f"expected only acme rows, leaked {leaked}")


@check(suite=S, target="ledger", id="NAI-LED-03",
       title="Unbalanced entries are refused",
       intent="Double-entry means the legs must sum to zero.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    ctx.step("post 500.00 debit against 400.00 credit")
    try:
        ledger.post_entry(store, {
            "idempotency_key": "bad-1", "currency": "EUR",
            "legs": [{"account": "cash", "amount_cents": 50000}, {"account": "revenue", "amount_cents": -40000}],
        }, ctx.active)
        refused = False
    except ledger.LedgerError:
        refused = True
    ctx.expect(refused, "an unbalanced entry should be refused")


@check(suite=S, target="ledger", id="NAI-LED-04",
       title="An account balance reflects what was posted",
       intent="Balances should aggregate the legs of an account.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    for i, amount in enumerate((1000, 2500, 400), start=1):
        ledger.post_entry(store, {
            "idempotency_key": f"bal-{i}", "currency": "EUR",
            "legs": [{"account": "cash", "amount_cents": amount},
                     {"account": "revenue", "amount_cents": -amount}],
        }, ctx.active)
    ctx.step("read the cash balance")
    ctx.expect(ledger.balance_of(store, "cash", "EUR", ctx.active) == 3900,
               f"expected 3900, got {ledger.balance_of(store, 'cash', 'EUR', ctx.active)}")
