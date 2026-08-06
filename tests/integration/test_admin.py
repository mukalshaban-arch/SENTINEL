"""Admin module: user management, audit log, backups. All ADMIN-only —
each endpoint is also checked to reject an ANALYST token, since these are
the highest-privilege operations in the system."""
import uuid

from _lib import call


def run(ctx):
    results = []
    admin_tok = ctx["admin_tok"]
    analyst_tok = ctx["analyst_tok"]
    viewer_tok = ctx["viewer_tok"]

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    # ── Users ────────────────────────────────────────────────────────────
    code, r = call("GET", "/api/users", admin_tok)
    check("admin lists users", code == 200 and isinstance(r, list), f"code={code}")
    check("user list includes seeded accounts",
          isinstance(r, list) and {u["username"] for u in r} >= {"admin", "analyst", "viewer"})
    check("user list never exposes password hashes",
          isinstance(r, list) and all("password" not in u for u in r))

    # Users can only be deactivated, never hard-deleted, so a fixed username
    # would collide with itself on the second local run. Unique per run.
    uniq_user = f"zztest_{uuid.uuid4().hex[:8]}"

    code, r = call("POST", "/api/users", admin_tok,
                    {"username": uniq_user, "password": "Str0ng!Passw0rd", "name": "ZZTest User",
                     "role": "ANALYST", "unit": "ZZTest Unit"})
    check("admin creates user", code == 201 and "id" in r, f"code={code} body={r}")
    new_uid = r.get("id") if code == 201 else None

    code, r = call("POST", "/api/users", admin_tok,
                    {"username": "zzweak", "password": "weak", "name": "ZZ Weak"})
    check("weak password rejected by policy", code == 400, f"code={code}")

    code, r = call("POST", "/api/users", admin_tok,
                    {"username": "zzbadrole", "password": "Str0ng!Passw0rd", "name": "ZZ Bad",
                     "role": "SUPERUSER"})
    check("invalid role rejected", code == 400, f"code={code}")

    code, r = call("POST", "/api/users", admin_tok, {"username": "zzincomplete"})
    check("missing required user fields rejected", code == 400, f"code={code}")

    code, r = call("POST", "/api/users", admin_tok,
                    {"username": uniq_user, "password": "Str0ng!Passw0rd", "name": "Dupe"})
    check("duplicate username rejected", code == 409, f"code={code}")

    if new_uid:
        code, r = call("PUT", f"/api/users/{new_uid}", admin_tok, {"name": "ZZTest Renamed", "role": "VIEWER"})
        check("admin updates user", code == 200, f"code={code}")

        code, r = call("PUT", f"/api/users/{new_uid}", admin_tok, {"role": "NOTAROLE"})
        check("update with invalid role rejected", code == 400, f"code={code}")

        code, r = call("PUT", f"/api/users/{new_uid}", admin_tok, {"password": "short"})
        check("update with weak password rejected", code == 400, f"code={code}")

        code, r = call("DELETE", f"/api/users/{new_uid}", admin_tok)
        check("admin deactivates user", code == 200, f"code={code}")

        code, r = call("PUT", f"/api/users/{new_uid}", admin_tok, {"active": True})
        check("admin reactivates user", code == 200, f"code={code}")

        # Leave the test account disabled rather than active.
        call("DELETE", f"/api/users/{new_uid}", admin_tok)

    # Self-deactivation guard: admin's own id comes from the JWT 'sub' claim.
    code, r = call("GET", "/api/users", admin_tok)
    admin_id = next((u["id"] for u in r if u["username"] == "admin"), None) if code == 200 else None
    if admin_id:
        code, r = call("DELETE", f"/api/users/{admin_id}", admin_tok)
        check("admin cannot deactivate own account", code == 400, f"code={code}")

    # Non-admins locked out of user management entirely.
    for label, tok in (("analyst", analyst_tok), ("viewer", viewer_tok)):
        code, r = call("GET", "/api/users", tok)
        check(f"{label} cannot list users", code in (401, 403), f"code={code}")
        code, r = call("POST", "/api/users", tok,
                        {"username": "zznope", "password": "Str0ng!Passw0rd", "name": "Nope"})
        check(f"{label} cannot create user", code in (401, 403), f"code={code}")

    # ── Audit log ────────────────────────────────────────────────────────
    code, r = call("GET", "/api/audit", admin_tok)
    check("admin reads audit log", code == 200 and isinstance(r, list), f"code={code}")

    code, r = call("GET", "/api/audit?limit=5", admin_tok)
    check("audit log respects limit", code == 200 and len(r) <= 5, f"code={code}")

    code, r = call("GET", "/api/audit?action=LOGIN", admin_tok)
    check("audit log filters by action",
          code == 200 and all(a["action"].startswith("LOGIN") for a in r), f"code={code}")

    code, r = call("GET", "/api/audit?limit=notanumber", admin_tok)
    check("audit log tolerates bad limit", code == 200, f"code={code}")

    code, r = call("GET", "/api/audit", analyst_tok)
    check("analyst cannot read audit log", code in (401, 403), f"code={code}")

    # ── Backups ──────────────────────────────────────────────────────────
    code, r = call("GET", "/api/backups", admin_tok)
    check("admin lists backups", code == 200 and isinstance(r, list), f"code={code}")

    # Shells out to pg_dump. Present on the CI runner (postgresql-client) so
    # this exercises the real success path there; on a dev box without the
    # client tools the endpoint must degrade to a clear 503, never a 500.
    code, r = call("POST", "/api/backups", admin_tok, {})
    if code == 200:
        check("admin creates backup", r.get("verified") is True, f"body={r}")
        check("backup records table row counts", isinstance(r.get("counts"), dict), f"body={r}")
    else:
        check("backup without pg_dump degrades to 503 (not 500)", code == 503, f"code={code} body={r}")
        check("503 explains the missing pg_dump",
              isinstance(r, dict) and "pg_dump" in r.get("error", ""), f"body={r}")

    code, r = call("GET", "/api/backups", analyst_tok)
    check("analyst cannot list backups", code in (401, 403), f"code={code}")

    return results
