"""Expert suite - the reference ceiling.

Written the way a careful engineer writes tests: exact expected values rather
than "greater than zero", both sides of every boundary, sequences that carry
state between calls, and a handful of invariants that hold for any input.

Every expected number in this file was produced by running the clean target and
reading the result, not by hand arithmetic.
"""

from __future__ import annotations

from decimal import Decimal as D

from ..targets import authn, ledger
from ..targets.checkout import price_cart
from . import Ctx, check
from ._kit import forge_claims, seeded_ledger, tamper_tail

S = "expert"


# --------------------------------------------------------------- checkout ---

@check(suite=S, target="checkout", id="EXP-CHK-01",
       title="Plain cart prices to the exact expected total",
       intent="Anchor the whole pricing pipeline on one exact value.")
def _(ctx: Ctx) -> None:
    ctx.step("price 5 x 2.00, no promo")
    r = price_cart([{"sku": "A", "unit_price": "2.00", "qty": 5}], ctx.active)
    ctx.expect(r["goods"] == D("9.50"), f"goods 9.50 after the 5% tier, got {r['goods']}")
    ctx.expect(r["shipping"] == D("4.99"), f"shipping 4.99 below threshold, got {r['shipping']}")
    ctx.expect(r["total"] == D("17.39"), f"total 17.39, got {r['total']}")


@check(suite=S, target="checkout", id="EXP-CHK-02",
       title="Quantity tier includes its lower boundary (qty 3)",
       intent="A tier advertised as 'from 3' must apply at exactly 3.")
def _(ctx: Ctx) -> None:
    ctx.step("price 3 x 10.00 - exactly the first tier boundary")
    r = price_cart([{"sku": "B", "unit_price": "10.00", "qty": 3}], ctx.active)
    ctx.expect(r["lines"][0]["tier_rate"] == D("0.05"), f"5% tier at qty 3, got {r['lines'][0]['tier_rate']}")
    ctx.expect(r["total"] == D("40.19"), f"total 40.19, got {r['total']}")


@check(suite=S, target="checkout", id="EXP-CHK-03",
       title="Quantity tiers include their boundaries at 6 and 12",
       intent="The same off-by-one can be seeded at any tier, so probe all of them.")
def _(ctx: Ctx) -> None:
    ctx.step("price 6 x 5.00 - second tier boundary")
    six = price_cart([{"sku": "C", "unit_price": "5.00", "qty": 6}], ctx.active)
    ctx.expect(six["total"] == D("38.39"), f"total 38.39 at qty 6, got {six['total']}")
    ctx.step("price 12 x 4.00 - third tier boundary")
    twelve = price_cart([{"sku": "D", "unit_price": "4.00", "qty": 12}], ctx.active)
    ctx.expect(twelve["total"] == D("54.95"), f"total 54.95 at qty 12, got {twelve['total']}")


@check(suite=S, target="checkout", id="EXP-CHK-04",
       title="Free shipping applies at exactly the threshold",
       intent="'Free over 50' has to mean free AT 50; this is the classic inclusive-bound bug.")
def _(ctx: Ctx) -> None:
    ctx.step("price 2 x 25.00 - goods land on exactly 50.00")
    r = price_cart([{"sku": "E", "unit_price": "25.00", "qty": 2}], ctx.active)
    ctx.expect(r["goods"] == D("50.00"), f"goods exactly 50.00, got {r['goods']}")
    ctx.expect(r["shipping"] == D("0.00"), f"shipping free at the threshold, got {r['shipping']}")
    ctx.expect(r["total"] == D("60.00"), f"total 60.00, got {r['total']}")


@check(suite=S, target="checkout", id="EXP-CHK-05",
       title="Shipping is charged just below and free just above the threshold",
       intent="Pin the other side of the boundary so a fix cannot overshoot.")
def _(ctx: Ctx) -> None:
    ctx.step("goods 49.98 - one line of 2 x 24.99")
    below = price_cart([{"sku": "F", "unit_price": "24.99", "qty": 2}], ctx.active)
    ctx.expect(below["shipping"] == D("4.99"), f"shipping charged below threshold, got {below['shipping']}")
    ctx.step("goods 50.02 - one line of 2 x 25.01")
    above = price_cart([{"sku": "F", "unit_price": "25.01", "qty": 2}], ctx.active)
    ctx.expect(above["shipping"] == D("0.00"), f"shipping free above threshold, got {above['shipping']}")


@check(suite=S, target="checkout", id="EXP-CHK-06",
       title="Promo percentage applies to goods, never to shipping",
       intent="A discount code must not quietly discount delivery.")
def _(ctx: Ctx) -> None:
    ctx.step("price 2 x 10.00 with SAVE10, below the free-shipping threshold")
    r = price_cart([{"sku": "G", "unit_price": "10.00", "qty": 2}], ctx.active, "SAVE10")
    ctx.expect(r["promo_discount"] == D("2.00"), f"discount is 10% of goods = 2.00, got {r['promo_discount']}")
    ctx.expect(r["shipping"] == D("4.99"), f"shipping still charged in full, got {r['shipping']}")
    ctx.expect(r["total"] == D("27.59"), f"total 27.59, got {r['total']}")


@check(suite=S, target="checkout", id="EXP-CHK-07",
       title="VAT falls when a promo is applied",
       intent="Tax is owed on what was actually charged, not on the pre-discount subtotal.")
def _(ctx: Ctx) -> None:
    ctx.step("price the same cart with and without SAVE25")
    cart = [{"sku": "H", "unit_price": "14.00", "qty": 10}]
    plain = price_cart(cart, ctx.active)
    promo = price_cart(cart, ctx.active, "SAVE25")
    ctx.expect(promo["vat"] < plain["vat"], f"VAT must drop with the discount: {promo['vat']} vs {plain['vat']}")
    ctx.expect(promo["vat"] == D("18.90"), f"VAT 18.90 on the discounted base, got {promo['vat']}")


@check(suite=S, target="checkout", id="EXP-CHK-08",
       title="Non-positive quantities are rejected",
       intent="A missing validation guard is invisible unless something invalid is sent.")
def _(ctx: Ctx) -> None:
    for qty in (0, -3):
        ctx.step(f"price a line with qty {qty}")
        try:
            price_cart([{"sku": "I", "unit_price": "5.00", "qty": qty}], ctx.active)
            raised = False
        except ValueError:
            raised = True
        ctx.expect(raised, f"qty {qty} must raise ValueError")


@check(suite=S, target="checkout", id="EXP-CHK-09",
       title="Invariant: goods equals the sum of line nets",
       intent="Structural invariant that must hold for every cart, defect or not.")
def _(ctx: Ctx) -> None:
    cart = [
        {"sku": "J", "unit_price": "3.30", "qty": 4},
        {"sku": "K", "unit_price": "12.10", "qty": 7},
        {"sku": "L", "unit_price": "0.99", "qty": 13},
    ]
    ctx.step("price a three-line cart spanning all three tiers")
    r = price_cart(cart, ctx.active)
    line_sum = sum((line["net"] for line in r["lines"]), D("0"))
    ctx.expect(abs(line_sum - r["goods"]) <= D("0.02"), f"line nets {line_sum} vs goods {r['goods']}")
    ctx.expect(r["promo_discount"] <= r["goods"], "a discount can never exceed goods")


@check(suite=S, target="checkout", id="EXP-CHK-10",
       title="An unknown promo code is a no-op",
       intent="Unrecognised codes must not error and must not discount.")
def _(ctx: Ctx) -> None:
    cart = [{"sku": "M", "unit_price": "9.00", "qty": 2}]
    ctx.step("price with a nonsense promo code")
    r = price_cart(cart, ctx.active, "NOT-A-CODE")
    ctx.expect(r["promo_discount"] == D("0.00"), f"no discount for an unknown code, got {r['promo_discount']}")
    ctx.expect(r["total"] == price_cart(cart, ctx.active)["total"], "unknown code must match no code at all")


# ------------------------------------------------------------------ authn ---

@check(suite=S, target="authn", id="EXP-AUT-01",
       title="Issue and verify round-trips the claims",
       intent="Baseline: the happy path works and the claims survive.")
def _(ctx: Ctx) -> None:
    ctx.step("issue a token for alice at t=1000, ttl 3600")
    token = authn.issue_token("alice", roles=["user"], scopes=["read"], iat=1000, ttl=3600)
    ctx.step("verify at t=2000")
    claims = authn.verify_token(token, now=2000, active=ctx.active, required_scope="read")
    ctx.expect(claims is not None and claims["sub"] == "alice", f"claims round-trip, got {claims}")
    ctx.expect(claims["exp"] == 4600, f"exp is iat+ttl, got {claims.get('exp')}")


@check(suite=S, target="authn", id="EXP-AUT-02",
       title="A token is rejected one second past expiry",
       intent="Expiry must bite at the edge; probing far past expiry proves nothing.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("bob", scopes=["read"], iat=1000, ttl=100)
    ctx.step("verify at exp+1 = 1101")
    try:
        authn.verify_token(token, now=1101, active=ctx.active)
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "a token one second past expiry must be refused")


@check(suite=S, target="authn", id="EXP-AUT-03",
       title="A token is still valid at exactly its expiry second",
       intent="Pin the inclusive side of the expiry bound so a fix cannot overshoot.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("bob", scopes=["read"], iat=1000, ttl=100)
    ctx.step("verify at exp = 1100")
    claims = authn.verify_token(token, now=1100, active=ctx.active)
    ctx.expect(claims is not None, "a token at exactly exp must still verify")


@check(suite=S, target="authn", id="EXP-AUT-04",
       title="A signature tampered only in its tail is rejected",
       intent="A truncated comparison passes garbage-signature tests but fails this one.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("carol", scopes=["read"], iat=0, ttl=1000)
    ctx.step("flip the final character of an otherwise valid signature")
    try:
        authn.verify_token(tamper_tail(token), now=10, active=ctx.active)
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "a signature altered anywhere must be refused")


@check(suite=S, target="authn", id="EXP-AUT-05",
       title="A privilege forgery is rejected on every one of 12 attempts",
       intent="Repeat the probe: an intermittently-skipped check is invisible to a single attempt.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("dave", roles=["user"], scopes=["read"], iat=0, ttl=10000)
    forged = forge_claims(token, roles=["admin"], scopes=["read", "write", "admin"])
    ctx.step("verify the same forged token 12 times")
    accepted = 0
    for _attempt in range(12):
        try:
            authn.verify_token(forged, now=10, active=ctx.active, required_scope="admin")
            accepted += 1
        except authn.AuthError:
            pass
    ctx.expect(accepted == 0, f"a forged token was accepted on {accepted} of 12 attempts")


@check(suite=S, target="authn", id="EXP-AUT-06",
       title="A role merely containing 'admin' does not bypass scopes",
       intent="Substring role matching is the classic silent authorisation hole.")
def _(ctx: Ctx) -> None:
    ctx.step("issue a token with role billing_admin and no scopes")
    token = authn.issue_token("erin", roles=["billing_admin"], scopes=[], iat=0, ttl=1000)
    try:
        authn.verify_token(token, now=10, active=ctx.active, required_scope="payouts:write")
        denied = False
    except authn.AuthError:
        denied = True
    ctx.expect(denied, "billing_admin must not inherit the admin bypass")


@check(suite=S, target="authn", id="EXP-AUT-07",
       title="A malformed token raises AuthError, not a falsy return",
       intent="The contract is claims-or-raise; a None return breaks every caller that binds it.")
def _(ctx: Ctx) -> None:
    ctx.step("verify the string 'not-a-token'")
    try:
        authn.verify_token("not-a-token", now=10, active=ctx.active)
        outcome = "returned normally"
    except authn.AuthError:
        outcome = "raised AuthError"
    ctx.expect(outcome == "raised AuthError", f"expected AuthError, the call {outcome}")


@check(suite=S, target="authn", id="EXP-AUT-08",
       title="Revoking a token by its id stops it verifying",
       intent="Needs two calls with state between them; a single-call test cannot see it.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("frank", scopes=["read"], iat=0, ttl=10000, jti="tok-frank-1")
    ctx.step("verify once - should succeed")
    authn.verify_token(token, now=10, active=ctx.active)
    ctx.step("revoke jti tok-frank-1 and verify again")
    try:
        authn.verify_token(token, now=20, active=ctx.active, revoked={"tok-frank-1"})
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "a revoked token id must stop verifying")


# ----------------------------------------------------------------- ledger ---

@check(suite=S, target="ledger", id="EXP-LED-01",
       title="Replaying an idempotency key posts exactly once",
       intent="The retry is the test; posting each fixture once can never see a broken key.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    entry = {
        "idempotency_key": "pay-42",
        "tenant": "acme",
        "currency": "EUR",
        "legs": [{"account": "cash", "amount_cents": 2500}, {"account": "revenue", "amount_cents": -2500}],
    }
    ctx.step("post entry pay-42")
    ledger.post_entry(store, entry, ctx.active)
    ctx.step("post the identical entry again (a client retry)")
    second = ledger.post_entry(store, entry, ctx.active)
    ctx.expect(second["duplicate"] is True, "the retry must be reported as a duplicate")
    ctx.expect(len(store["entries"]) == 1, f"ledger must hold 1 entry, holds {len(store['entries'])}")
    ctx.expect(ledger.balance_of(store, "cash", "EUR", ctx.active) == 2500,
               f"cash balance must be 2500, is {ledger.balance_of(store, 'cash', 'EUR', ctx.active)}")


@check(suite=S, target="ledger", id="EXP-LED-02",
       title="A small unbalanced entry is refused",
       intent="Invariants get bypassed for 'cheap' rows; probe under the cheap threshold.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    ctx.step("post an entry of 4.00 debit against 3.00 credit")
    try:
        ledger.post_entry(store, {
            "idempotency_key": "small-1",
            "currency": "EUR",
            "legs": [{"account": "cash", "amount_cents": 400}, {"account": "revenue", "amount_cents": -300}],
        }, ctx.active)
        refused = False
    except ledger.LedgerError:
        refused = True
    ctx.expect(refused, "an unbalanced entry must be refused whatever its size")
    ctx.expect(len(store["entries"]) == 0, f"nothing may be stored, found {len(store['entries'])}")


@check(suite=S, target="ledger", id="EXP-LED-03",
       title="A large unbalanced entry is refused",
       intent="The other side of the size threshold, so a fix cannot pass by narrowing it.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    ctx.step("post an entry of 400.00 debit against 300.00 credit")
    try:
        ledger.post_entry(store, {
            "idempotency_key": "big-1",
            "currency": "EUR",
            "legs": [{"account": "cash", "amount_cents": 40000}, {"account": "revenue", "amount_cents": -30000}],
        }, ctx.active)
        refused = False
    except ledger.LedgerError:
        refused = True
    ctx.expect(refused, "an unbalanced entry must be refused whatever its size")


@check(suite=S, target="ledger", id="EXP-LED-04",
       title="Adjacent pages are disjoint and contiguous",
       intent="A page-edge defect is only visible when two pages are compared to each other.")
def _(ctx: Ctx) -> None:
    store = seeded_ledger(ctx.active)
    ctx.step("read page 1 and page 2 at per_page=5")
    p1 = ledger.list_entries(store, page=1, per_page=5, active=ctx.active)
    p2 = ledger.list_entries(store, page=2, per_page=5, active=ctx.active)
    ids1 = [r["id"] for r in p1["items"]]
    ids2 = [r["id"] for r in p2["items"]]
    ctx.expect(not set(ids1) & set(ids2), f"pages must not overlap: {ids1} then {ids2}")
    ctx.expect(ids2[0] == ids1[-1] + 1, f"page 2 must continue from page 1: {ids1[-1]} then {ids2[0]}")


@check(suite=S, target="ledger", id="EXP-LED-05",
       title="An account balance is scoped to one currency",
       intent="Mixed-currency ledgers are where a missing filter becomes a wrong number.")
def _(ctx: Ctx) -> None:
    store = seeded_ledger(ctx.active)
    ctx.step("ask for the EUR balance of cash in a EUR+USD ledger")
    eur = ledger.balance_of(store, "cash", "EUR", ctx.active)
    usd = ledger.balance_of(store, "cash", "USD", ctx.active)
    ctx.expect(eur == 54000, f"EUR cash balance must be 54000, is {eur}")
    ctx.expect(usd == 24000, f"USD cash balance must be 24000, is {usd}")


@check(suite=S, target="ledger", id="EXP-LED-06",
       title="An unfiltered listing is still scoped to the caller's tenant",
       intent="Tenant leaks hide on the default path, which is the path nobody filters.")
def _(ctx: Ctx) -> None:
    store = seeded_ledger(ctx.active)
    ctx.step("list entries for tenant globex with no other filter")
    page = ledger.list_entries(store, page=1, per_page=20, tenant="globex", active=ctx.active)
    foreign = [r["id"] for r in page["items"] if r["tenant"] != "globex"]
    ctx.expect(not foreign, f"rows from another tenant leaked: {foreign}")
    ctx.expect(page["total"] == 4, f"globex owns 4 entries, listing reported {page['total']}")
