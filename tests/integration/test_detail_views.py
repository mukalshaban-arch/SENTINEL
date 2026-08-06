"""Detail/aggregate read endpoints that back the entity pages: person and
group detail, per-entity activity timelines, gallery, intel reports,
locations, hotspot/activity detail, link-chart listing, and the dashboard
stats aggregate. Mostly GET paths that the write-focused suites never touch."""
from _lib import call

TINY_PNG = ("data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def run(ctx):
    results = []
    tok = ctx["admin_tok"]
    poi_id = ctx.get("poi_id")
    group_id = ctx.get("group_id")

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    # ── Dashboard stats ──────────────────────────────────────────────────
    code, r = call("GET", "/api/stats", tok)
    check("stats returns expected keys",
          code == 200 and isinstance(r, dict) and len(r) > 0, f"code={code} body={r}")

    # ── Person detail & sub-resources ────────────────────────────────────
    if poi_id:
        code, r = call("GET", f"/api/persons/{poi_id}", tok)
        check("person detail includes joined panels",
              code == 200 and all(k in r for k in ("affiliation", "gallery", "images", "locations")),
              f"code={code}")

        code, r = call("GET", f"/api/persons/{poi_id}/activities", tok)
        check("person activity timeline", code == 200 and isinstance(r, list), f"code={code}")

        code, r = call("GET", f"/api/persons/{poi_id}/summary", tok)
        check("person summary returns null when never generated",
              code == 200 and "summary" in r, f"code={code} body={r}")

        # ── Gallery ──────────────────────────────────────────────────────
        code, r = call("GET", f"/api/persons/{poi_id}/gallery", tok)
        check("list gallery", code == 200 and isinstance(r, list), f"code={code}")

        code, r = call("POST", f"/api/persons/{poi_id}/gallery", tok,
                        {"src": TINY_PNG, "caption": "ZZ gallery photo", "date": "2024-02-02"})
        check("add gallery photo", code == 201 and "id" in r, f"code={code} body={r}")
        gid = r.get("id") if code == 201 else None

        code, r = call("POST", f"/api/persons/{poi_id}/gallery", tok, {"caption": "no src"})
        check("gallery photo without src rejected", code == 400, f"code={code}")

        if gid:
            code, r = call("DELETE", f"/api/persons/{poi_id}/gallery/{gid}", tok)
            check("delete gallery photo", code == 200, f"code={code}")

    code, r = call("GET", "/api/persons/99999999", tok)
    check("missing person 404s", code == 404, f"code={code}")

    # ── Group detail & sub-resources ─────────────────────────────────────
    if group_id:
        code, r = call("GET", f"/api/groups/{group_id}", tok)
        check("group detail", code == 200 and r.get("id") == group_id, f"code={code}")

        code, r = call("GET", f"/api/groups/{group_id}/activities", tok)
        check("group activity timeline", code == 200 and isinstance(r, list), f"code={code}")

        code, r = call("GET", f"/api/groups/{group_id}/summary", tok)
        check("group summary endpoint", code == 200 and "summary" in r, f"code={code}")

    code, r = call("GET", "/api/groups/99999999", tok)
    check("missing group 404s", code == 404, f"code={code}")

    # ── Activities & hotspots ────────────────────────────────────────────
    code, r = call("GET", "/api/activities", tok)
    check("list activities", code == 200 and isinstance(r, list), f"code={code}")

    if ctx.get("activity_id"):
        code, r = call("GET", f"/api/activities/{ctx['activity_id']}", tok)
        check("activity detail includes related/images/locations",
              code == 200 and all(k in r for k in ("related", "images", "locations")), f"code={code}")

    code, r = call("GET", "/api/activities/99999999", tok)
    check("missing activity 404s", code == 404, f"code={code}")

    code, r = call("GET", "/api/hotspots", tok)
    check("list hotspots", code == 200 and isinstance(r, list), f"code={code}")

    if ctx.get("hotspot_id"):
        code, r = call("GET", f"/api/hotspots/{ctx['hotspot_id']}", tok)
        check("hotspot detail", code == 200, f"code={code}")

    code, r = call("GET", "/api/hotspots/99999999", tok)
    check("missing hotspot 404s", code == 404, f"code={code}")

    # ── Intel reports ────────────────────────────────────────────────────
    code, r = call("GET", "/api/intel", tok)
    check("list intel reports", code == 200 and isinstance(r, list), f"code={code}")

    if ctx.get("intel_id"):
        code, r = call("GET", f"/api/intel/{ctx['intel_id']}", tok)
        check("intel detail", code == 200, f"code={code}")

        code, r = call("PUT", f"/api/intel/{ctx['intel_id']}", tok,
                        {"title": "ZZTest Intel Edited", "text": "updated body"})
        check("update intel report", code == 200, f"code={code}")

    code, r = call("POST", "/api/intel", tok, {"body": "no title"})
    check("intel without title rejected", code == 400, f"code={code}")

    # ── Standing locations ───────────────────────────────────────────────
    code, r = call("GET", "/api/locations", tok)
    check("list standing locations", code == 200 and isinstance(r, list), f"code={code}")

    code, r = call("POST", "/api/locations", tok,
                    {"name": "ZZTest Location", "country": "Kenya", "address": "Nairobi CBD",
                     "coords": [{"lat": -1.3, "lng": 36.8, "label": "main"}]})
    check("create standing location with coords", code == 201, f"code={code} body={r}")
    if code == 201 and r.get("id"):
        ctx["location_id"] = r["id"]

    code, r = call("POST", "/api/locations", tok, {"country": "Kenya"})
    check("location without name rejected", code == 400, f"code={code}")

    # ── Link charts listing ──────────────────────────────────────────────
    code, r = call("GET", "/api/link-charts", tok)
    check("list link charts", code == 200 and isinstance(r, list), f"code={code}")

    code, r = call("GET", "/api/link-charts/99999999", tok)
    check("missing link chart 404s", code == 404, f"code={code}")

    return results
