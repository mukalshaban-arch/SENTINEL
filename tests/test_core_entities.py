"""Core records: dashboard stats, person/group/activity/hotspot create+update.
Leaves ctx['poi_id'], ctx['group_id'], ctx['activity_id'], ctx['hotspot_id']
for later modules (link analysis, cleanup) to use."""
from _lib import call


def run(ctx):
    results = []
    tok = ctx["admin_tok"]

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    code, r = call("GET", "/api/stats", tok)
    check("dashboard stats", code == 200, f"code={code}")

    code, r = call("POST", "/api/persons", tok, {"alias": "ZZTest Person", "nationality": "Kenyan"})
    check("create person", code == 201 and "id" in r, f"code={code} body={r}")
    ctx["poi_id"] = r.get("id") if code == 201 else None

    if ctx["poi_id"]:
        code, r = call("PUT", f"/api/persons/{ctx['poi_id']}", tok, {"riskLevel": "HIGH"})
        check("update person", code == 200, f"code={code}")

        code, r = call("GET", f"/api/persons/{ctx['poi_id']}", tok)
        check("get person round-trips edit", code == 200 and r.get("risk_level") == "HIGH", f"code={code}")

    code, r = call("POST", "/api/groups", tok, {"name": "ZZTest Group", "base": "Nairobi, Kenya"})
    check("create group", code == 201, f"code={code} body={r}")
    ctx["group_id"] = r.get("id") if code == 201 else None

    if ctx["group_id"]:
        code, r = call("PUT", f"/api/groups/{ctx['group_id']}", tok, {"threatLevel": "HIGH"})
        check("update group", code == 200, f"code={code}")

    if ctx["poi_id"]:
        code, r = call("POST", "/api/activities", tok,
                        {"poiId": ctx["poi_id"], "type": "MEETING", "date": "2024-01-01", "location": "Nairobi",
                         "lat": -1.29, "lng": 36.82, "description": "ZZTest activity", "severity": "LOW"})
        check("create activity", code == 201, f"code={code} body={r}")
        ctx["activity_id"] = r.get("id") if code == 201 else None

        if ctx["activity_id"]:
            code, r = call("PUT", f"/api/activities/{ctx['activity_id']}", tok, {"severity": "HIGH"})
            check("update activity", code == 200, f"code={code}")

    code, r = call("POST", "/api/hotspots", tok,
                    {"name": "ZZTest Hotspot", "lat": -1.3, "lng": 36.8, "type": "GENERAL", "risk": "LOW"})
    check("create hotspot", code == 201, f"code={code} body={r}")
    ctx["hotspot_id"] = r.get("id") if code == 201 else None

    if ctx["hotspot_id"]:
        code, r = call("PUT", f"/api/hotspots/{ctx['hotspot_id']}", tok, {"risk": "HIGH"})
        check("update hotspot", code == 200, f"code={code}")

    code, r = call("POST", "/api/intel", tok, {"title": "ZZTest Intel", "body": "test report"})
    check("create intel report", code == 201, f"code={code} body={r}")
    ctx["intel_id"] = r.get("id") if code == 201 else None

    return results
