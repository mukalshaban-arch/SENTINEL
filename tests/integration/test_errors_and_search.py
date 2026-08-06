"""Search/filter query params, auth failure modes, and malformed-input
handling. These drive the error branches in server.py that the happy-path
suites never reach — the code most likely to break unnoticed."""
from _lib import call


def run(ctx):
    results = []
    tok = ctx["admin_tok"]

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    # ── Search / filtering ───────────────────────────────────────────────
    code, r = call("GET", "/api/persons?q=ZZTest", tok)
    check("person search matches by alias",
          code == 200 and any("ZZTest" in (p.get("alias") or "") for p in r), f"code={code}")

    code, r = call("GET", "/api/persons?q=Kenyan", tok)
    check("person search matches by nationality", code == 200 and isinstance(r, list), f"code={code}")

    code, r = call("GET", "/api/persons?q=zzzz-no-such-person-zzzz", tok)
    check("person search with no matches returns empty list", code == 200 and r == [], f"code={code}")

    code, r = call("GET", "/api/groups?q=ZZTest", tok)
    check("group search", code == 200 and isinstance(r, list), f"code={code}")

    code, r = call("GET", "/api/activities?q=ZZTest", tok)
    check("activity search by description/location", code == 200 and isinstance(r, list), f"code={code}")

    code, r = call("GET", "/api/activities?date_from=2020-01-01&date_to=2030-01-01", tok)
    check("activity date-range filter", code == 200 and isinstance(r, list), f"code={code}")

    code, r = call("GET", "/api/locations?q=ZZTest", tok)
    check("location search", code == 200 and isinstance(r, list), f"code={code}")

    # SQL-injection shaped input must be parameterised away, not executed.
    code, r = call("GET", "/api/persons?q=%27%3B%20DROP%20TABLE%20poi%3B--", tok)
    check("sql-injection-shaped search is handled safely", code == 200, f"code={code}")
    code, r = call("GET", "/api/persons", tok)
    check("poi table still intact after injection attempt", code == 200 and isinstance(r, list))

    # ── Auth failure modes ───────────────────────────────────────────────
    code, r = call("GET", "/api/persons")
    check("no token rejected", code == 401, f"code={code}")

    code, r = call("GET", "/api/persons", "not-a-real-jwt")
    check("garbage token rejected", code == 401, f"code={code}")

    code, r = call("GET", "/api/persons", tok[:-4] + "AAAA")
    check("tampered token signature rejected", code == 401, f"code={code}")

    code, r = call("POST", "/api/auth/login", body={"username": "admin"})
    check("login without password rejected", code == 400, f"code={code}")

    code, r = call("POST", "/api/auth/login", body={"username": "", "password": ""})
    check("login with empty credentials rejected", code == 400, f"code={code}")

    code, r = call("POST", "/api/auth/login", body={"username": "nosuchuser", "password": "Whatever1!"})
    check("login as unknown user rejected", code == 401, f"code={code}")

    code, r = call("POST", "/api/auth/logout", tok, {})
    check("logout succeeds", code == 200, f"code={code}")

    code, r = call("POST", "/api/auth/logout", body={})
    check("logout without token still returns ok", code == 200, f"code={code}")

    # ── Malformed bodies ─────────────────────────────────────────────────
    code, r = call("POST", "/api/persons", tok, b"{not valid json", is_json=False)
    check("malformed JSON body rejected", code == 400, f"code={code}")

    code, r = call("POST", "/api/auth/login", body=b"{broken", is_json=False)
    check("malformed login body rejected", code == 400, f"code={code}")

    code, r = call("POST", "/api/persons", tok, {"alias": ""})
    check("person without alias rejected", code == 400, f"code={code}")

    code, r = call("POST", "/api/groups", tok, {})
    check("group without name rejected", code == 400, f"code={code}")

    # ── Routing ──────────────────────────────────────────────────────────
    code, r = call("GET", "/api/definitely-not-an-endpoint", tok)
    check("unknown API route 404s", code == 404, f"code={code}")

    code, r = call("DELETE", "/api/stats", tok)
    check("unsupported method on known route 404s", code == 404, f"code={code}")

    # ── Static file serving / path traversal ─────────────────────────────
    code, r = call("GET", "/login.html", is_json=False)
    check("static file served", code == 200, f"code={code}")

    code, r = call("GET", "/../server.py", is_json=False)
    check("path traversal blocked", code in (400, 403, 404), f"code={code}")

    code, r = call("GET", "/no-such-page.html", is_json=False)
    check("missing static file 404s", code == 404, f"code={code}")

    # ── Country profile edge cases ───────────────────────────────────────
    code, r = call("GET", "/api/countries/%20", tok)
    check("blank country name rejected", code == 404, f"code={code}")

    return results
