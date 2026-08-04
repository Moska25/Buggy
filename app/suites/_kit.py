"""Fixture helpers shared by more than one suite.

Deliberately thin. Where two suites build the *same* input differently that is
signal about the suites, so only genuinely mechanical helpers live here.
"""

from __future__ import annotations

import base64
import json

from ..targets import ledger


def seeded_ledger(active: set[str], count: int = 12) -> dict:
    """A ledger with `count` balanced entries across two tenants and two currencies.

    Every entry is balanced and uses a unique idempotency key, so building the
    fixture is itself unaffected by any seeded defect.
    """
    store = ledger.new_store()
    for i in range(1, count + 1):
        amount = 1000 * i
        ledger.post_entry(
            store,
            {
                "idempotency_key": f"seed-{i}",
                "tenant": "globex" if i % 3 == 0 else "acme",
                "currency": "USD" if i % 4 == 0 else "EUR",
                "memo": f"seed entry {i}",
                "legs": [
                    {"account": "cash", "amount_cents": amount},
                    {"account": "revenue", "amount_cents": -amount},
                ],
            },
            active,
        )
    return store


def tamper_tail(token: str) -> str:
    """Flip the last character of the signature, leaving the prefix intact."""
    body, sig = token.split(".", 1)
    last = "0" if sig[-1] != "0" else "1"
    return f"{body}.{sig[:-1]}{last}"


def forge_claims(token: str, **overrides) -> str:
    """Rewrite the payload and keep the old signature - a plain privilege forgery."""
    body, sig = token.split(".", 1)
    claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    claims.update(overrides)
    raw = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    new_body = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"{new_body}.{sig}"
