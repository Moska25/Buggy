"""Target 2 of 3: token issue and verification.

A small HMAC-signed bearer token: base64url(payload).hex(signature). Real
signature checking, real expiry, real scope authorisation, real revocation by
token id - and six seeded defects that each weaken exactly one of those.

The security defects here are the interesting ones for the benchmark because
they are invisible to any suite that only asserts the happy path: a shallow
"a valid token verifies, a garbage token does not" pair passes cleanly against
every single one of them.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Iterable

from . import rng

DEFAULT_SECRET = b"buggy-benchmark-secret"

#: AUT-001 accepts tokens this long past their expiry.
LEEWAY_SECONDS = 3600

#: AUT-006 skips signature verification on roughly this share of calls.
FAST_PATH_SHARE = 0.30


class AuthError(Exception):
    """Raised for any token that must not be trusted."""


def issue_token(
    sub: str,
    roles: Iterable[str] = (),
    scopes: Iterable[str] = (),
    iat: int = 0,
    ttl: int = 3600,
    jti: str | None = None,
    secret: bytes = DEFAULT_SECRET,
) -> str:
    payload = {
        "sub": sub,
        "roles": sorted(roles),
        "scopes": sorted(scopes),
        "iat": int(iat),
        "exp": int(iat) + int(ttl),
        "jti": jti or f"{sub}-{int(iat)}",
    }
    body = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return f"{body}.{_sign(body, secret)}"


def verify_token(
    token: str,
    now: int,
    active: Iterable[str] | None = None,
    required_scope: str | None = None,
    revoked: Iterable[str] = (),
    secret: bytes = DEFAULT_SECRET,
) -> dict[str, Any]:
    """Return the claims of a trustworthy token, or raise AuthError."""
    active = set(active or ())
    revoked = set(revoked)

    try:
        body, signature = token.split(".", 1)
        claims = json.loads(base64.urlsafe_b64decode(_pad(body)))
        if not isinstance(claims, dict):
            raise ValueError("claims must be an object")
    except Exception as exc:
        if "AUT-004" in active:
            # Contract break: a malformed token yields None instead of raising,
            # so `if verify_token(...)` callers are fine but
            # `claims = verify_token(...)` callers carry a None into the session.
            return None  # type: ignore[return-value]
        raise AuthError(f"malformed token: {exc}") from exc

    _check_signature(body, signature, secret, active)
    _check_expiry(claims, now, active)
    _check_revocation(claims, revoked, active)
    _check_scope(claims, required_scope, active)
    return claims


def _check_signature(body: str, signature: str, secret: bytes, active: set[str]) -> None:
    expected = _sign(body, secret)

    if "AUT-006" in active and rng.flaky(FAST_PATH_SHARE):
        # A "load-shedding fast path" that samples signature verification to
        # save CPU. Forged tokens get through on the sampled fraction of calls,
        # which is why this defect is the only nondeterministic one in Buggy.
        return

    if "AUT-002" in active:
        # Truncated comparison: only the first 8 hex characters are checked, so
        # a forgery only has to match 32 bits of the digest.
        if signature[:8] != expected[:8]:
            raise AuthError("bad signature")
        return

    if not hmac.compare_digest(signature, expected):
        raise AuthError("bad signature")


def _check_expiry(claims: dict[str, Any], now: int, active: set[str]) -> None:
    exp = int(claims.get("exp", 0))
    if "AUT-001" in active:
        # A grace window added "for clock skew". It is an hour wide, so an
        # expired token keeps working long after it should have died - but a
        # probe far past expiry still gets rejected, which is exactly why a
        # lazily-written expiry test misses this.
        if now > exp + LEEWAY_SECONDS:
            raise AuthError("token expired")
        return
    if now > exp:
        raise AuthError("token expired")


def _check_revocation(claims: dict[str, Any], revoked: set[str], active: set[str]) -> None:
    if "AUT-005" in active:
        # Revocation is matched against the subject while the revocation list
        # holds token ids, so revoking a token never matches anything.
        if claims.get("sub") in revoked:
            raise AuthError("token revoked")
        return
    if claims.get("jti") in revoked:
        raise AuthError("token revoked")


def _check_scope(claims: dict[str, Any], required_scope: str | None, active: set[str]) -> None:
    if not required_scope:
        return
    scopes = set(claims.get("scopes", ()))
    roles = list(claims.get("roles", ()))

    if "AUT-003" in active:
        # Substring role test: intended to let the `admin` role through, it also
        # lets `billing_admin`, `admin_readonly` and friends skip the scope
        # check entirely. This is the missing authorisation check.
        if any("admin" in role for role in roles):
            return
    elif "admin" in roles:
        return

    if required_scope not in scopes:
        raise AuthError(f"missing scope {required_scope}")


def _sign(body: str, secret: bytes) -> str:
    return hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _pad(body: str) -> bytes:
    return (body + "=" * (-len(body) % 4)).encode()
