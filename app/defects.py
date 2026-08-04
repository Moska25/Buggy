"""The seeded defect catalog.

Every id here corresponds to exactly one `if "<id>" in active:` branch inside
app/targets/. The runner builds one variant of the system per defect, with that
single defect active and nothing else, plus one clean build with none active.

Framing: a seeded defect is a mutant. Mutation testing normally uses mutants to
grade the code; Buggy inverts it and uses them to grade the test suites.

`hint` is the probe a tester would have to construct to see the defect at all.
It is what the /defects pages show, and it is the honest explanation for why a
shallow suite misses a defect - not "the suite is bad", but "the suite never
built this input".
"""

from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = (
    "correctness",
    "boundary",
    "security",
    "contract",
    "state",
    "nondeterminism",
)
SEVERITIES = ("blocker", "major", "minor")

TARGETS = {
    "checkout": "Cart pricing: tiers, promos, shipping threshold, VAT.",
    "authn": "Token issue and verification: expiry, signature, scope, revocation.",
    "ledger": "Double-entry ledger: idempotency, invariants, pagination, currency.",
}


@dataclass(frozen=True)
class Defect:
    id: str
    target: str
    title: str
    description: str
    category: str
    severity: str
    hint: str

    @property
    def severity_pill(self) -> str:
        return {"blocker": "pill-fail", "major": "pill-warn", "minor": "pill-idle"}[self.severity]


DEFECTS: tuple[Defect, ...] = (
    # ---------------- checkout ----------------
    Defect(
        id="CHK-001",
        target="checkout",
        title="Promo percentage discounts shipping too",
        description=(
            "The promo code percentage is applied to goods plus shipping instead of goods "
            "alone, so every discount code silently discounts delivery as well."
        ),
        category="correctness",
        severity="major",
        hint=(
            "Price a cart below the free-shipping threshold with a promo code applied, and "
            "assert the promo discount equals the percentage of goods only. A cart that "
            "already qualifies for free shipping cannot see this defect."
        ),
    ),
    Defect(
        id="CHK-002",
        target="checkout",
        title="Quantity discount tier excludes its own boundary",
        description=(
            "The tier test is `qty > minimum` rather than `qty >= minimum`, so a line of "
            "exactly 3, 6 or 12 units is charged at the tier below the one advertised."
        ),
        category="boundary",
        severity="major",
        hint=(
            "Price lines at exactly 3, 6 and 12 units. Quantities either side of a boundary "
            "behave correctly, so only the boundary values themselves expose it."
        ),
    ),
    Defect(
        id="CHK-003",
        target="checkout",
        title="Total rounds half-to-even instead of half-up",
        description=(
            "The single final quantize uses banker's rounding. Identical to the correct "
            "result on 99% of carts; one cent low on an exact half-cent tie."
        ),
        category="correctness",
        severity="minor",
        hint=(
            "Construct a cart whose pre-rounding total lands exactly on a half cent with an "
            "even preceding digit - 5 units at 1.41 gives 14.605 pre-VAT-rounding and is the "
            "cheapest such cart. Measured by brute force, only about 1% of single-line carts "
            "expose this at all."
        ),
    ),
    Defect(
        id="CHK-004",
        target="checkout",
        title="Free-shipping threshold is exclusive",
        description=(
            "Free shipping tests `goods > 50.00` instead of `>= 50.00`, so an order of "
            "exactly the advertised threshold is charged the delivery fee."
        ),
        category="boundary",
        severity="major",
        hint=(
            "Price a cart whose goods total is exactly 50.00 and assert shipping is zero. "
            "49.99 and 50.01 both behave correctly."
        ),
    ),
    Defect(
        id="CHK-005",
        target="checkout",
        title="VAT computed on the pre-discount subtotal",
        description=(
            "Tax is calculated from goods plus shipping, ignoring the promo discount, so "
            "every discounted order is overcharged VAT on money the customer never paid."
        ),
        category="correctness",
        severity="blocker",
        hint=(
            "Price the same cart with and without a promo code and assert the VAT falls in "
            "proportion. Checking only the discount line, or only an undiscounted cart, "
            "misses it entirely."
        ),
    ),
    Defect(
        id="CHK-006",
        target="checkout",
        title="Non-positive quantity validation dropped",
        description=(
            "The guard rejecting qty <= 0 is gone. A negative line quantity is accepted and "
            "becomes a silent credit against the order total."
        ),
        category="contract",
        severity="minor",
        hint=(
            "Assert that a cart line with qty 0 or -1 raises ValueError. Any suite that only "
            "feeds valid carts cannot see a missing validation guard."
        ),
    ),
    # ---------------- authn ----------------
    Defect(
        id="AUT-001",
        target="authn",
        title="Expired tokens accepted inside a one-hour grace window",
        description=(
            "A 3600-second leeway was added 'for clock skew'. Tokens keep verifying for a "
            "full hour after they expire."
        ),
        category="security",
        severity="blocker",
        hint=(
            "Verify a token at exactly one second past expiry. Probing far past expiry - the "
            "obvious way to write an expiry test - still gets rejected, so the defect hides "
            "from anyone who does not test at the edge."
        ),
    ),
    Defect(
        id="AUT-002",
        target="authn",
        title="Signature compared on its first 8 characters only",
        description=(
            "The HMAC comparison is truncated to 8 hex characters, reducing a 256-bit "
            "signature to 32 bits of real protection."
        ),
        category="security",
        severity="blocker",
        hint=(
            "Tamper with the tail of a valid signature and assert verification fails. "
            "Replacing the whole signature with garbage is still rejected, so the standard "
            "'a bad signature is refused' assertion passes."
        ),
    ),
    Defect(
        id="AUT-003",
        target="authn",
        title="Substring role test bypasses the scope check",
        description=(
            "The admin bypass matches any role *containing* 'admin', so roles such as "
            "billing_admin or admin_readonly skip scope authorisation entirely."
        ),
        category="security",
        severity="major",
        hint=(
            "Issue a token whose role merely contains the substring 'admin' and no scopes, "
            "then demand a privileged scope. Testing the literal roles 'admin' and 'user' "
            "shows correct behaviour in both directions."
        ),
    ),
    Defect(
        id="AUT-004",
        target="authn",
        title="Malformed token returns None instead of raising",
        description=(
            "The documented contract is claims-or-AuthError. A malformed token now returns "
            "None, so callers that bind the result carry a None identity into the session."
        ),
        category="contract",
        severity="minor",
        hint=(
            "Assert that garbage input raises AuthError specifically, not merely that it is "
            "falsy. `assert not verify_token(...)` passes against this defect."
        ),
    ),
    Defect(
        id="AUT-005",
        target="authn",
        title="Revocation matched against subject instead of token id",
        description=(
            "The revocation list holds token ids but is checked against the subject claim, "
            "so revoking a token has no effect at all."
        ),
        category="state",
        severity="major",
        hint=(
            "Issue a token, revoke it by its jti, then verify it again and expect rejection. "
            "Requires carrying state between two calls; a single-call test cannot see it."
        ),
    ),
    Defect(
        id="AUT-006",
        target="authn",
        title="Signature verification sampled by a load-shedding fast path",
        description=(
            "A performance 'fast path' skips signature verification on roughly 30% of calls. "
            "A forged token is therefore accepted intermittently rather than never."
        ),
        category="nondeterminism",
        severity="major",
        hint=(
            "Verify a forged token repeatedly rather than once. A single probe catches this "
            "about 30% of the time, so a suite that asserts it once is itself flaky - which "
            "is what the flake-rate column measures."
        ),
    ),
    # ---------------- ledger ----------------
    Defect(
        id="LED-001",
        target="ledger",
        title="Idempotency guard narrowed to zero-amount entries",
        description=(
            "The dedupe guard now only fires when the entry amount is zero, so any real "
            "retry of a payment posts a second time and the ledger double-counts."
        ),
        category="state",
        severity="blocker",
        hint=(
            "Post the identical entry twice with the same idempotency key and assert the "
            "ledger holds one row. A suite that posts each fixture once cannot see it."
        ),
    ),
    Defect(
        id="LED-002",
        target="ledger",
        title="Double-entry invariant skipped for small entries",
        description=(
            "Entries whose largest leg is under 10.00 bypass the balance check, so "
            "unbalanced small entries are accepted and corrupt every downstream balance."
        ),
        category="correctness",
        severity="blocker",
        hint=(
            "Post a deliberately unbalanced entry *under* 10.00 and assert it is refused. "
            "An unbalanced entry over the threshold is still correctly refused."
        ),
    ),
    Defect(
        id="LED-003",
        target="ledger",
        title="Page offset off by one after the first page",
        description=(
            "Pages after the first start one row early, so every page boundary repeats the "
            "previous page's last row and a paged export double-counts."
        ),
        category="contract",
        severity="major",
        hint=(
            "Read two adjacent pages and assert their ids are disjoint and contiguous. "
            "Reading page 1 alone, or checking only page length, shows nothing wrong."
        ),
    ),
    Defect(
        id="LED-004",
        target="ledger",
        title="Account balance sums across currencies",
        description=(
            "The currency filter is ignored, so EUR and USD legs are added together as if "
            "the rate were 1.0 and the reported balance is meaningless."
        ),
        category="correctness",
        severity="major",
        hint=(
            "Seed one account with entries in two currencies, then ask for the balance in "
            "one of them. A single-currency ledger cannot expose this."
        ),
    ),
    Defect(
        id="LED-005",
        target="ledger",
        title="Tenant filter dropped on the unfiltered listing",
        description=(
            "When no account filter is supplied the tenant filter is skipped entirely, so "
            "the default listing returns every tenant's entries."
        ),
        category="security",
        severity="major",
        hint=(
            "List entries for one tenant with no other filter, in a store holding more than "
            "one tenant, and assert every row belongs to the caller. Listing with an account "
            "filter applies the tenant filter correctly."
        ),
    ),
)

BY_ID: dict[str, Defect] = {d.id: d for d in DEFECTS}

#: The single nondeterministic defect. The runner re-runs this build to measure flake.
NONDETERMINISTIC_ID = "AUT-006"


def by_target(target: str) -> list[Defect]:
    return [d for d in DEFECTS if d.target == target]


def category_counts() -> dict[str, int]:
    return {c: sum(1 for d in DEFECTS if d.category == c) for c in CATEGORIES}
