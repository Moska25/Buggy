"""Clean-build behaviour of the token target."""

import pytest

from app.suites._kit import forge_claims, tamper_tail
from app.targets import authn

CLEAN: set[str] = set()


def test_issue_and_verify_round_trips_claims():
    token = authn.issue_token("alice", roles=["user"], scopes=["read"], iat=1000, ttl=3600)
    claims = authn.verify_token(token, now=2000, active=CLEAN)
    assert claims["sub"] == "alice"
    assert claims["roles"] == ["user"]
    assert claims["exp"] == 4600


def test_token_is_valid_at_exactly_its_expiry_second():
    token = authn.issue_token("bob", iat=1000, ttl=100)
    assert authn.verify_token(token, now=1100, active=CLEAN)["sub"] == "bob"


def test_token_is_rejected_one_second_past_expiry():
    token = authn.issue_token("bob", iat=1000, ttl=100)
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=1101, active=CLEAN)


def test_tail_tampered_signature_is_rejected():
    token = authn.issue_token("carol", iat=0, ttl=1000)
    with pytest.raises(authn.AuthError):
        authn.verify_token(tamper_tail(token), now=10, active=CLEAN)


def test_forged_claims_are_rejected():
    token = authn.issue_token("dave", roles=["user"], scopes=["read"], iat=0, ttl=1000)
    forged = forge_claims(token, roles=["admin"], scopes=["admin"])
    with pytest.raises(authn.AuthError):
        authn.verify_token(forged, now=10, active=CLEAN)


@pytest.mark.parametrize("bad", ["", "not-a-token", "garbage.garbage", "a.b.c"])
def test_malformed_tokens_raise_autherror(bad):
    with pytest.raises(authn.AuthError):
        authn.verify_token(bad, now=10, active=CLEAN)


def test_missing_scope_is_refused():
    token = authn.issue_token("erin", roles=["user"], scopes=["read"], iat=0, ttl=1000)
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=10, active=CLEAN, required_scope="write")


def test_present_scope_is_allowed():
    token = authn.issue_token("erin", roles=["user"], scopes=["read", "write"], iat=0, ttl=1000)
    assert authn.verify_token(token, now=10, active=CLEAN, required_scope="write")


def test_admin_role_bypasses_the_scope_requirement():
    token = authn.issue_token("root", roles=["admin"], scopes=[], iat=0, ttl=1000)
    assert authn.verify_token(token, now=10, active=CLEAN, required_scope="anything")


@pytest.mark.parametrize("role", ["billing_admin", "admin_readonly", "sysadmin"])
def test_role_merely_containing_admin_does_not_bypass_scopes(role):
    token = authn.issue_token("mallory", roles=[role], scopes=[], iat=0, ttl=1000)
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=10, active=CLEAN, required_scope="payouts:write")


def test_revoking_by_token_id_stops_verification():
    token = authn.issue_token("frank", iat=0, ttl=1000, jti="tok-1")
    assert authn.verify_token(token, now=10, active=CLEAN)
    with pytest.raises(authn.AuthError):
        authn.verify_token(token, now=10, active=CLEAN, revoked={"tok-1"})


def test_revoking_a_different_token_id_has_no_effect():
    token = authn.issue_token("frank", iat=0, ttl=1000, jti="tok-1")
    assert authn.verify_token(token, now=10, active=CLEAN, revoked={"tok-2"})


def test_verification_is_deterministic_on_the_clean_build():
    token = authn.issue_token("gina", iat=0, ttl=1000)
    forged = forge_claims(token, roles=["admin"])
    for _ in range(50):
        with pytest.raises(authn.AuthError):
            authn.verify_token(forged, now=10, active=CLEAN)
