"""
SENTINEL – auth.py
Hardened authentication helpers:
  - bcrypt password hashing
  - JWT signing/verification (secret loaded from env, never hardcoded)
  - Brute-force / rate-limit protection (DB-backed, works across threads)
  - Password policy enforcement
  - Role-based access helpers
"""

import os
import re
import time
import hmac
import hashlib
import base64
import json
import logging
from datetime import datetime, timezone, timedelta

import bcrypt

from db import db_cursor

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# JWT – secret must come from environment
# ──────────────────────────────────────────────
def _jwt_secret() -> bytes:
    secret = os.environ.get("SENTINEL_JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError(
            "SENTINEL_JWT_SECRET is not set or is too short (min 32 chars). "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret.encode()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


def issue_token(user_id: int, username: str, role: str,
                ttl_hours: int = 12) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    exp = int(time.time()) + ttl_hours * 3600
    payload = _b64url(json.dumps({
        "sub": user_id,
        "usr": username,
        "role": role,
        "exp": exp,
    }).encode())
    sig = _b64url(
        hmac.new(_jwt_secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> dict | None:
    """Returns payload dict or None if invalid/expired."""
    try:
        header, payload, sig = token.split(".")
    except ValueError:
        return None

    expected_sig = _b64url(
        hmac.new(_jwt_secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        data = json.loads(_b64url_decode(payload))
    except Exception:
        return None

    if data.get("exp", 0) < time.time():
        return None

    return data


# ──────────────────────────────────────────────
# Password policy
# ──────────────────────────────────────────────
PASSWORD_MIN_LEN = 10
PASSWORD_RULES = [
    (r"[A-Z]", "at least one uppercase letter"),
    (r"[a-z]", "at least one lowercase letter"),
    (r"[0-9]", "at least one digit"),
    (r"[^A-Za-z0-9]", "at least one special character"),
]


def validate_password(password: str) -> list[str]:
    """Returns list of violation strings (empty = OK)."""
    errors = []
    if len(password) < PASSWORD_MIN_LEN:
        errors.append(f"at least {PASSWORD_MIN_LEN} characters")
    for pattern, msg in PASSWORD_RULES:
        if not re.search(pattern, password):
            errors.append(msg)
    return errors


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ──────────────────────────────────────────────
# Brute-force protection
# ──────────────────────────────────────────────
LOCKOUT_WINDOW_SECONDS = 600   # 10 minutes
LOCKOUT_MAX_FAILURES   = 10    # failures before lockout
LOCKOUT_DURATION_SECONDS = 900 # 15 minutes


def record_attempt(username: str, ip: str, success: bool) -> None:
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO login_attempts (username, ip, success) VALUES (%s, %s, %s)",
            (username.lower(), ip, success)
        )


def is_locked_out(username: str, ip: str) -> bool:
    """
    True if either the username or the IP has exceeded the failure threshold
    in the last LOCKOUT_WINDOW_SECONDS and the lockout duration hasn't passed.
    """
    window_start = datetime.now(timezone.utc) - timedelta(seconds=LOCKOUT_WINDOW_SECONDS)
    with db_cursor() as cur:
        # Check by username
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM login_attempts
            WHERE username = %s
              AND success = FALSE
              AND attempted_at >= %s
        """, (username.lower(), window_start))
        row = cur.fetchone()
        if row and row["cnt"] >= LOCKOUT_MAX_FAILURES:
            return True

        # Check by IP
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM login_attempts
            WHERE ip = %s
              AND success = FALSE
              AND attempted_at >= %s
        """, (ip, window_start))
        row = cur.fetchone()
        if row and row["cnt"] >= LOCKOUT_MAX_FAILURES:
            return True

    return False


# ──────────────────────────────────────────────
# Request-level auth helpers (used in server.py)
# ──────────────────────────────────────────────
def get_token_from_header(headers: dict) -> str | None:
    auth = headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def require_auth(headers: dict, min_role: str = "VIEWER") -> dict:
    """
    Validates the JWT in the Authorization header.
    Raises PermissionError with an HTTP-friendly message on failure.

    Role hierarchy: VIEWER < ANALYST < ADMIN
    Role strings are uppercase throughout (DB, JWT payload, API responses)
    to match the frontend's role checks (e.g. `['ADMIN','ANALYST'].includes(user.role)`).
    """
    ROLE_RANK = {"VIEWER": 0, "ANALYST": 1, "ADMIN": 2}

    token = get_token_from_header(headers)
    if not token:
        raise PermissionError("401: Missing or malformed Authorization header.")

    payload = verify_token(token)
    if not payload:
        raise PermissionError("401: Invalid or expired token.")

    user_rank = ROLE_RANK.get(payload.get("role", ""), -1)
    min_rank  = ROLE_RANK.get(min_role.upper(), 99)
    if user_rank < min_rank:
        raise PermissionError(f"403: Role '{min_role}' or higher required.")

    return payload
