"""Country Profiles: aggregation, lookup, garbage-name rejection, known-list."""
from _lib import call


def run(ctx):
    results = []
    tok = ctx["admin_tok"]

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    code, r = call("GET", "/api/countries", tok)
    check("list countries", code == 200 and isinstance(r, list), f"code={code}")

    check("Kenya present (from ZZTest Person)",
          isinstance(r, list) and any(c.get("name") == "Kenya" for c in r))

    code, r = call("GET", "/api/countries/Kenya", tok)
    check("get Kenya profile", code == 200 and r.get("name") == "Kenya", f"code={code}")

    code, r = call("GET", "/api/countries/NotARealCountryXYZ", tok)
    check("garbage country rejected", code == 404, f"code={code}")

    code, r = call("GET", "/api/countries/known-list", tok)
    check("known country list has 100+ entries", code == 200 and isinstance(r, list) and len(r) > 100,
          f"code={code} count={len(r) if isinstance(r, list) else '?'}")

    return results
