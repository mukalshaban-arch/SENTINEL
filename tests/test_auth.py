"""Auth: login for all three default roles, bad-password rejection."""
from _lib import call, login


def run(ctx):
    results = []

    tok = login("admin", "Sentinel@2024!")
    results.append(("PASS" if tok else "FAIL", "admin login", "" if tok else "no token returned"))
    ctx["admin_tok"] = tok

    tok = login("analyst", "Sentinel@2024!")
    results.append(("PASS" if tok else "FAIL", "analyst login", "" if tok else "no token returned"))
    ctx["analyst_tok"] = tok

    tok = login("viewer", "Sentinel@2024!")
    results.append(("PASS" if tok else "FAIL", "viewer login", "" if tok else "no token returned"))
    ctx["viewer_tok"] = tok

    code, r = call("POST", "/api/auth/login", body={"username": "admin", "password": "wrongpassword"})
    results.append(("PASS" if code == 401 else "FAIL", "bad password rejected", f"code={code}"))

    return results
