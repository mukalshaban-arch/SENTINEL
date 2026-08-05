"""Deletes every ZZTest* record this suite created, using the admin token."""
from _lib import call


def run(ctx):
    tok = ctx.get("admin_tok")
    if not tok:
        return

    if ctx.get("chart_id"):
        call("DELETE", f"/api/link-charts/{ctx['chart_id']}", tok)
    if ctx.get("intel_id"):
        call("DELETE", f"/api/intel/{ctx['intel_id']}", tok)
    if ctx.get("hotspot_id"):
        call("DELETE", f"/api/hotspots/{ctx['hotspot_id']}", tok)
    if ctx.get("activity_id"):
        call("DELETE", f"/api/activities/{ctx['activity_id']}", tok)
    if ctx.get("group_id"):
        call("DELETE", f"/api/groups/{ctx['group_id']}", tok)
    if ctx.get("poi_id"):
        call("DELETE", f"/api/persons/{ctx['poi_id']}", tok)

    # Sweep for any ZZTest/ZZFail leftovers from a prior interrupted run.
    code, persons = call("GET", "/api/persons", tok)
    if code == 200:
        for p in persons:
            if str(p.get("alias", "")).startswith(("ZZTest", "ZZFail")):
                call("DELETE", f"/api/persons/{p['id']}", tok)

    code, groups = call("GET", "/api/groups", tok)
    if code == 200:
        for g in groups:
            if str(g.get("name", "")).startswith(("ZZTest", "ZZFail")):
                call("DELETE", f"/api/groups/{g['id']}", tok)
