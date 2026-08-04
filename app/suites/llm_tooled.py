"""LLM suite, code-reading condition - RECORDED FIXTURE.

Read this header before reading the checks.

This file is a committed fixture, exactly like llm_naive.py. It was authored
once to represent the code-reading condition - checks written with the target
source visible and the freedom to execute it while drafting - and then checked
in so the benchmark is reproducible and runs offline. Buggy does not call a
model at run time, requires no API key, and never regenerates a suite live.
Live generation is Phase 6 in TODO.md and is not built.

Reading the code buys exact expected values and real boundary probes, and it
shows: this suite finds most of what the expert suite finds. What it does not
buy is the instinct to ask "what else could be true?" - it never probes a role
that merely *contains* 'admin', never builds a two-currency ledger, and never
lists without a filter. Those three defects survive it.
"""

from __future__ import annotations

from decimal import Decimal as D

from ..targets import authn, ledger
from ..targets.checkout import price_cart
from . import Ctx, check
from ._kit import forge_claims, seeded_ledger, tamper_tail

S = "llm_tooled"


@check(suite=S, target="checkout", id="TOO-CHK-01",
       title="Baseline cart prices to an exact total",
       intent="Pin the whole pipeline to a value read off the clean implementation.")
def _(ctx: Ctx) -> None:
    ctx.step("price 5 x 2.00")
    r = price_cart([{"sku": "A", "unit_price": "2.00", "qty": 5}], ctx.active)
    ctx.expect(r["goods"] == D("9.50"), f"goods 9.50, got {r['goods']}")
    ctx.expect(r["total"] == D("17.39"), f"total 17.39, got {r['total']}")


@check(suite=S, target="checkout", id="TOO-CHK-02",
       title="The 5% tier applies at exactly 3 units",
       intent="Tier bounds are inclusive; test the boundary value itself.")
def _(ctx: Ctx) -> None:
    ctx.step("price 3 x 10.00")
    r = price_cart([{"sku": "B", "unit_price": "10.00", "qty": 3}], ctx.active)
    ctx.expect(r["lines"][0]["tier_rate"] == D("0.05"), f"5% tier at 3 units, got {r['lines'][0]['tier_rate']}")


@check(suite=S, target="checkout", id="TOO-CHK-03",
       title="The 15% tier applies at exactly 12 units",
       intent="Same boundary logic at the top tier.")
def _(ctx: Ctx) -> None:
    ctx.step("price 12 x 4.00")
    r = price_cart([{"sku": "C", "unit_price": "4.00", "qty": 12}], ctx.active)
    ctx.expect(r["total"] == D("54.95"), f"total 54.95, got {r['total']}")


@check(suite=S, target="checkout", id="TOO-CHK-04",
       title="Shipping is free at exactly 50.00 of goods",
       intent="The threshold is inclusive in the spec; probe the exact amount.")
def _(ctx: Ctx) -> None:
    ctx.step("price 2 x 25.00 for goods of exactly 50.00")
    r = price_cart([{"sku": "D", "unit_price": "25.00", "qty": 2}], ctx.active)
    ctx.expect(r["shipping"] == D("0.00"), f"free at the threshold, got {r['shipping']}")


@check(suite=S, target="checkout", id="TOO-CHK-05",
       title="A promo discounts goods and leaves shipping alone",
       intent="Separate the two amounts so a discount cannot bleed into delivery.")
def _(ctx: Ctx) -> None:
    ctx.step("price 2 x 10.00 with SAVE10 below the threshold")
    r = price_cart([{"sku": "E", "unit_price": "10.00", "qty": 2}], ctx.active, "SAVE10")
    ctx.expect(r["promo_discount"] == D("2.00"), f"discount 2.00, got {r['promo_discount']}")
    ctx.expect(r["shipping"] == D("4.99"), f"shipping untouched at 4.99, got {r['shipping']}")


@check(suite=S, target="checkout", id="TOO-CHK-06",
       title="VAT is charged on the discounted base",
       intent="Tax base must be what is actually payable.")
def _(ctx: Ctx) -> None:
    ctx.step("price 10 x 14.00 with SAVE25")
    r = price_cart([{"sku": "F", "unit_price": "14.00", "qty": 10}], ctx.active, "SAVE25")
    ctx.expect(r["vat"] == D("18.90"), f"VAT 18.90 on the discounted base, got {r['vat']}")
    ctx.expect(r["total"] == D("113.40"), f"total 113.40, got {r['total']}")


@check(suite=S, target="checkout", id="TOO-CHK-07",
       title="Zero and negative quantities raise",
       intent="Validation must reject a line that cannot exist.")
def _(ctx: Ctx) -> None:
    for qty in (0, -2):
        ctx.step(f"price a line with qty {qty}")
        try:
            price_cart([{"sku": "G", "unit_price": "5.00", "qty": qty}], ctx.active)
            raised = False
        except ValueError:
            raised = True
        ctx.expect(raised, f"qty {qty} must raise ValueError")


@check(suite=S, target="checkout", id="TOO-CHK-08",
       title="Line net equals gross minus the tier discount",
       intent="Internal consistency of a single line.")
def _(ctx: Ctx) -> None:
    ctx.step("price 7 x 6.40 and inspect the line arithmetic")
    line = price_cart([{"sku": "H", "unit_price": "6.40", "qty": 7}], ctx.active)["lines"][0]
    ctx.expect(line["net"] == line["gross"] - line["tier_discount"],
               f"net {line['net']} != gross {line['gross']} - discount {line['tier_discount']}")


@check(suite=S, target="authn", id="TOO-AUT-01",
       title="Issue and verify round-trip",
       intent="Baseline happy path with claims inspection.")
def _(ctx: Ctx) -> None:
    ctx.step("issue for alice, verify with the required scope")
    token = authn.issue_token("alice", roles=["user"], scopes=["read"], iat=1000, ttl=3600)
    claims = authn.verify_token(token, now=2000, active=ctx.active, required_scope="read")
    ctx.expect(claims and claims["sub"] == "alice", f"expected alice, got {claims}")


@check(suite=S, target="authn", id="TOO-AUT-02",
       title="Expiry bites one second past exp",
       intent="Read the comparison in the code and probe immediately past it.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("bob", scopes=["read"], iat=1000, ttl=100)
    ctx.step("verify at 1101, one second past exp")
    try:
        authn.verify_token(token, now=1101, active=ctx.active)
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "expired by one second must be refused")


@check(suite=S, target="authn", id="TOO-AUT-03",
       title="A signature altered in its last character is rejected",
       intent="Guard against a comparison that only inspects a prefix.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("carol", scopes=["read"], iat=0, ttl=1000)
    ctx.step("flip the last signature character")
    try:
        authn.verify_token(tamper_tail(token), now=10, active=ctx.active)
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "a tampered signature must be refused")


@check(suite=S, target="authn", id="TOO-AUT-04",
       title="A forged privilege escalation is rejected on 4 attempts",
       intent="Repeat the probe a few times in case verification is not deterministic.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("dave", roles=["user"], scopes=["read"], iat=0, ttl=10000)
    forged = forge_claims(token, roles=["admin"], scopes=["admin"])
    ctx.step("verify the forged token 4 times")
    accepted = 0
    for _attempt in range(4):
        try:
            authn.verify_token(forged, now=10, active=ctx.active, required_scope="admin")
            accepted += 1
        except authn.AuthError:
            pass
    ctx.expect(accepted == 0, f"forged token accepted on {accepted} of 4 attempts")


@check(suite=S, target="authn", id="TOO-AUT-05",
       title="Malformed input raises AuthError",
       intent="Assert the exception type, not merely a falsy result.")
def _(ctx: Ctx) -> None:
    ctx.step("verify a malformed token string")
    try:
        authn.verify_token("garbage.garbage", now=10, active=ctx.active)
        outcome = "returned"
    except authn.AuthError:
        outcome = "raised"
    ctx.expect(outcome == "raised", f"expected AuthError, the call {outcome}")


@check(suite=S, target="authn", id="TOO-AUT-06",
       title="Revocation by token id takes effect",
       intent="Verify before and after revoking the same token.")
def _(ctx: Ctx) -> None:
    token = authn.issue_token("erin", scopes=["read"], iat=0, ttl=10000, jti="tok-erin-3")
    ctx.step("verify, then revoke tok-erin-3 and verify again")
    authn.verify_token(token, now=10, active=ctx.active)
    try:
        authn.verify_token(token, now=20, active=ctx.active, revoked={"tok-erin-3"})
        rejected = False
    except authn.AuthError:
        rejected = True
    ctx.expect(rejected, "a revoked token id must be refused")


@check(suite=S, target="authn", id="TOO-AUT-07",
       title="The admin role bypasses the scope requirement",
       intent="Confirm the documented bypass works for the admin role.")
def _(ctx: Ctx) -> None:
    ctx.step("issue role=admin with no scopes, demand a scope")
    token = authn.issue_token("frank", roles=["admin"], scopes=[], iat=0, ttl=1000)
    claims = authn.verify_token(token, now=10, active=ctx.active, required_scope="payouts:write")
    ctx.expect(bool(claims), "admin must be allowed through without the scope")


@check(suite=S, target="ledger", id="TOO-LED-01",
       title="An idempotency key collapses a retry",
       intent="Post twice and count rows, not just the return flag.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    entry = {
        "idempotency_key": "ord-99", "currency": "EUR",
        "legs": [{"account": "cash", "amount_cents": 7500}, {"account": "revenue", "amount_cents": -7500}],
    }
    ctx.step("post ord-99 twice")
    ledger.post_entry(store, entry, ctx.active)
    second = ledger.post_entry(store, entry, ctx.active)
    ctx.expect(second["duplicate"] is True, "the retry must report duplicate")
    ctx.expect(len(store["entries"]) == 1, f"expected 1 row, found {len(store['entries'])}")


@check(suite=S, target="ledger", id="TOO-LED-02",
       title="A small unbalanced entry is refused",
       intent="Probe under any plausible 'cheap path' threshold in the invariant.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    ctx.step("post 2.00 debit against 1.50 credit")
    try:
        ledger.post_entry(store, {
            "idempotency_key": "tiny-1", "currency": "EUR",
            "legs": [{"account": "cash", "amount_cents": 200}, {"account": "revenue", "amount_cents": -150}],
        }, ctx.active)
        refused = False
    except ledger.LedgerError:
        refused = True
    ctx.expect(refused, "a small unbalanced entry must still be refused")


@check(suite=S, target="ledger", id="TOO-LED-03",
       title="Consecutive pages do not overlap",
       intent="Compare two adjacent pages rather than checking one in isolation.")
def _(ctx: Ctx) -> None:
    store = seeded_ledger(ctx.active)
    ctx.step("read pages 1 and 2 at per_page=5 and compare ids")
    p1 = [r["id"] for r in ledger.list_entries(store, page=1, per_page=5, active=ctx.active)["items"]]
    p2 = [r["id"] for r in ledger.list_entries(store, page=2, per_page=5, active=ctx.active)["items"]]
    ctx.expect(not set(p1) & set(p2), f"pages overlap: {p1} then {p2}")


@check(suite=S, target="ledger", id="TOO-LED-04",
       title="A balance aggregates the legs of one account",
       intent="Post a few entries and read the account total back.")
def _(ctx: Ctx) -> None:
    store = ledger.new_store()
    for i, amount in enumerate((1200, 3400), start=1):
        ledger.post_entry(store, {
            "idempotency_key": f"agg-{i}", "currency": "EUR",
            "legs": [{"account": "cash", "amount_cents": amount},
                     {"account": "revenue", "amount_cents": -amount}],
        }, ctx.active)
    ctx.step("read the EUR cash balance")
    got = ledger.balance_of(store, "cash", "EUR", ctx.active)
    ctx.expect(got == 4600, f"expected 4600, got {got}")


@check(suite=S, target="ledger", id="TOO-LED-05",
       title="Listing by account is scoped to the tenant",
       intent="Check isolation on the filtered listing path.")
def _(ctx: Ctx) -> None:
    store = seeded_ledger(ctx.active)
    ctx.step("list account=cash for tenant globex")
    page = ledger.list_entries(store, page=1, per_page=20, tenant="globex", account="cash", active=ctx.active)
    leaked = [r["id"] for r in page["items"] if r["tenant"] != "globex"]
    ctx.expect(not leaked, f"expected only globex rows, leaked {leaked}")
