"""Unit tests for auth.py: JWT issue/verify, password policy, hashing,
header parsing, and role-hierarchy enforcement. All pure/local — the two
functions that touch the DB (record_attempt, is_locked_out) are covered
separately via fake_db_cursor.
"""
import time

import pytest

import auth


# ── JWT ──────────────────────────────────────────────────────────────────
def test_issue_and_verify_roundtrip():
    token = auth.issue_token(user_id=1, username="admin", role="ADMIN")
    payload = auth.verify_token(token)
    assert payload is not None
    assert payload["sub"] == 1
    assert payload["usr"] == "admin"
    assert payload["role"] == "ADMIN"


def test_verify_rejects_malformed_token():
    assert auth.verify_token("not-a-jwt") is None
    assert auth.verify_token("only.two") is None
    assert auth.verify_token("") is None


def test_verify_rejects_tampered_signature():
    token = auth.issue_token(user_id=1, username="admin", role="ADMIN")
    header, payload, sig = token.split(".")
    tampered = f"{header}.{payload}.{sig[:-1]}x"
    assert auth.verify_token(tampered) is None


def test_verify_rejects_tampered_payload():
    token = auth.issue_token(user_id=1, username="viewer", role="VIEWER")
    header, payload, sig = token.split(".")
    # Swap in a different (validly-encoded) payload — signature won't match.
    forged_payload = auth._b64url(b'{"sub":1,"usr":"viewer","role":"ADMIN","exp":9999999999}')
    forged = f"{header}.{forged_payload}.{sig}"
    assert auth.verify_token(forged) is None


def test_verify_rejects_expired_token():
    token = auth.issue_token(user_id=1, username="admin", role="ADMIN", ttl_hours=-1)
    assert auth.verify_token(token) is None


def test_jwt_secret_too_short_raises(monkeypatch):
    monkeypatch.setenv("SENTINEL_JWT_SECRET", "short")
    with pytest.raises(RuntimeError):
        auth.issue_token(1, "x", "VIEWER")


# ── Password policy ─────────────────────────────────────────────────────
@pytest.mark.parametrize("password", [
    "Str0ng!Passw0rd",
    "Another$Val1dOne",
])
def test_validate_password_accepts_strong_passwords(password):
    assert auth.validate_password(password) == []


@pytest.mark.parametrize("password,expected_substring", [
    ("short1!A", "at least 10 characters"),
    ("alllowercase1!", "at least one uppercase letter"),
    ("ALLUPPERCASE1!", "at least one lowercase letter"),
    ("NoDigitsHere!", "at least one digit"),
    ("NoSpecial1234", "at least one special character"),
])
def test_validate_password_flags_each_rule(password, expected_substring):
    errors = auth.validate_password(password)
    assert any(expected_substring in e for e in errors)


def test_validate_password_reports_multiple_violations():
    errors = auth.validate_password("weak")
    # too short + no upper + no digit + no special = 4 violations (has lowercase)
    assert len(errors) == 4


# ── Password hashing ─────────────────────────────────────────────────────
def test_hash_and_check_password_roundtrip():
    hashed = auth.hash_password("Str0ng!Passw0rd")
    assert auth.check_password("Str0ng!Passw0rd", hashed)
    assert not auth.check_password("WrongPassword1!", hashed)


def test_hash_password_is_salted():
    h1 = auth.hash_password("Str0ng!Passw0rd")
    h2 = auth.hash_password("Str0ng!Passw0rd")
    assert h1 != h2  # bcrypt salts each hash differently


# ── Header parsing ────────────────────────────────────────────────────────
def test_get_token_from_header_extracts_bearer_token():
    assert auth.get_token_from_header({"Authorization": "Bearer abc.def.ghi"}) == "abc.def.ghi"


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": ""},
    {"Authorization": "Basic abc123"},
    {"Authorization": "Bearerabc"},
])
def test_get_token_from_header_returns_none_when_missing_or_malformed(headers):
    assert auth.get_token_from_header(headers) is None


# ── require_auth role hierarchy ────────────────────────────────────────
def _auth_header_for(role):
    token = auth.issue_token(user_id=1, username="u", role=role)
    return {"Authorization": f"Bearer {token}"}


def test_require_auth_missing_header_raises_401():
    with pytest.raises(PermissionError, match="401"):
        auth.require_auth({}, min_role="VIEWER")


def test_require_auth_invalid_token_raises_401():
    with pytest.raises(PermissionError, match="401"):
        auth.require_auth({"Authorization": "Bearer garbage"}, min_role="VIEWER")


@pytest.mark.parametrize("role,min_role", [
    ("VIEWER", "VIEWER"),
    ("ANALYST", "VIEWER"),
    ("ANALYST", "ANALYST"),
    ("ADMIN", "VIEWER"),
    ("ADMIN", "ANALYST"),
    ("ADMIN", "ADMIN"),
])
def test_require_auth_allows_sufficient_role(role, min_role):
    payload = auth.require_auth(_auth_header_for(role), min_role=min_role)
    assert payload["role"] == role


@pytest.mark.parametrize("role,min_role", [
    ("VIEWER", "ANALYST"),
    ("VIEWER", "ADMIN"),
    ("ANALYST", "ADMIN"),
])
def test_require_auth_blocks_insufficient_role(role, min_role):
    with pytest.raises(PermissionError, match="403"):
        auth.require_auth(_auth_header_for(role), min_role=min_role)


# ── DB-backed helpers (mocked) ────────────────────────────────────────────
def test_record_attempt_inserts_lowercased_username(fake_db_cursor):
    auth.record_attempt("ViewerUser", "127.0.0.1", success=False)
    args = fake_db_cursor.execute.call_args[0]
    assert args[1][0] == "vieweruser"


def test_is_locked_out_true_when_failures_exceed_threshold(fake_db_cursor):
    fake_db_cursor.fetchone.return_value = {"cnt": auth.LOCKOUT_MAX_FAILURES}
    assert auth.is_locked_out("someuser", "127.0.0.1") is True


def test_is_locked_out_false_when_under_threshold(fake_db_cursor):
    fake_db_cursor.fetchone.return_value = {"cnt": 0}
    assert auth.is_locked_out("someuser", "127.0.0.1") is False
