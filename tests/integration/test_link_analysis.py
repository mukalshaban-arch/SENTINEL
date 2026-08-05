"""Link Analysis: chart CRUD, node add (person/country), garbage-country
rejection, relationship drawing, chart load resolving nodes+edges."""
from _lib import call


def run(ctx):
    results = []
    tok = ctx["admin_tok"]
    poi_id = ctx.get("poi_id")

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    code, r = call("POST", "/api/link-charts", tok, {"name": "ZZTest Chart"})
    check("create link chart", code == 201, f"code={code} body={r}")
    ctx["chart_id"] = r.get("id") if code == 201 else None
    chart_id = ctx["chart_id"]
    if not chart_id:
        return results

    if poi_id:
        code, r = call("POST", f"/api/link-charts/{chart_id}/nodes", tok,
                        {"nodeType": "person", "nodeRef": str(poi_id), "x": 10, "y": 10})
        check("add person node", code == 201, f"code={code} body={r}")

    code, r = call("POST", f"/api/link-charts/{chart_id}/nodes", tok,
                    {"nodeType": "country", "nodeRef": "Kenya", "x": 100, "y": 100})
    check("add country node", code == 201, f"code={code} body={r}")

    code, r = call("POST", f"/api/link-charts/{chart_id}/nodes", tok,
                    {"nodeType": "country", "nodeRef": "Nowhereistan", "x": 0, "y": 0})
    check("garbage country node rejected", code == 400, f"code={code}")

    if poi_id:
        code, r = call("POST", f"/api/person/{poi_id}/relationships", tok,
                        {"relatedType": "country", "relatedName": "Kenya", "relType": "ZZTest link"})
        check("draw person-country relationship", code == 201, f"code={code} body={r}")

    code, r = call("GET", f"/api/link-charts/{chart_id}", tok)
    ok = code == 200 and len(r.get("nodes", [])) >= 1
    check("load chart resolves nodes", ok,
          f"code={code} nodes={len(r.get('nodes', [])) if code == 200 else '?'}")

    code, r = call("PUT", f"/api/link-charts/{chart_id}", tok, {"name": "ZZTest Chart Renamed"})
    check("update link chart", code == 200, f"code={code}")

    return results
