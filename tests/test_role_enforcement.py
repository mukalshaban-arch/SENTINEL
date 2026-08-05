"""Role/access-control: VIEWER must be blocked server-side (not just UI) on
every mutating endpoint; ANALYST/ADMIN must be unaffected. See _lib and
server.py's _require_edit_role for background — this whole module exists
because that guard was originally missing everywhere except deletes."""
from _lib import call


def run(ctx):
    results = []
    admin_tok = ctx["admin_tok"]
    analyst_tok = ctx["analyst_tok"]
    viewer_tok = ctx["viewer_tok"]
    poi_id = ctx.get("poi_id")

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    # Reads: everyone with a valid token can read.
    code, r = call("GET", "/api/persons", viewer_tok)
    check("viewer CAN read persons", code == 200, f"code={code}")

    code, r = call("GET", "/api/users", analyst_tok)
    check("analyst cannot list users", code in (401, 403), f"code={code}")

    code, r = call("GET", "/api/users", admin_tok)
    check("admin CAN list users", code == 200, f"code={code}")

    # Writes: viewer blocked everywhere.
    code, r = call("POST", "/api/persons", viewer_tok, {"alias": "ZZFail Person"})
    check("viewer cannot create person", code in (401, 403), f"code={code}")

    code, r = call("POST", "/api/groups", viewer_tok, {"name": "ZZFail Group"})
    check("viewer cannot create group", code in (401, 403), f"code={code}")

    code, r = call("POST", "/api/activities", viewer_tok, {"type": "MEETING", "date": "2024-01-01"})
    check("viewer cannot create activity", code in (401, 403), f"code={code}")

    code, r = call("POST", "/api/hotspots", viewer_tok, {"name": "ZZFail Hotspot", "lat": 0, "lng": 0})
    check("viewer cannot create hotspot", code in (401, 403), f"code={code}")

    code, r = call("POST", "/api/intel", viewer_tok, {"title": "ZZFail Intel"})
    check("viewer cannot create intel", code in (401, 403), f"code={code}")

    code, r = call("POST", "/api/link-charts", viewer_tok, {"name": "ZZFail Chart"})
    check("viewer cannot create link chart", code in (401, 403), f"code={code}")

    code, r = call("POST", "/api/nlp/submit", viewer_tok, {"text": "ZZFail nlp submit"})
    check("viewer cannot submit nlp job", code in (401, 403), f"code={code}")

    if poi_id:
        code, r = call("POST", f"/api/person/{poi_id}/tags", viewer_tok, {"tag": "zzfail"})
        check("viewer cannot add tag (extras POST)", code in (401, 403), f"code={code}")

        code, r = call("GET", f"/api/person/{poi_id}/tags", viewer_tok)
        check("viewer CAN read tags (extras GET)", code == 200, f"code={code}")

        # Analyst must still succeed — confirms the fix didn't over-block.
        code, r = call("POST", f"/api/person/{poi_id}/tags", analyst_tok, {"tag": "zztest"})
        check("analyst CAN add tag (extras POST)", code == 201, f"code={code} body={r}")
        if code == 201:
            call("DELETE", f"/api/tags/{r.get('id')}", admin_tok)

    code, r = call("POST", "/api/groups", analyst_tok, {"name": "ZZTest Analyst Group", "base": "Lagos, Nigeria"})
    check("analyst CAN create group", code == 201, f"code={code} body={r}")
    if code == 201:
        call("DELETE", f"/api/groups/{r.get('id')}", admin_tok)

    # Deletes: only ADMIN/ANALYST (existing pre-fix behavior, still true).
    code, r = call("DELETE", "/api/persons/999999999", viewer_tok)
    check("viewer cannot delete (even a nonexistent record)", code in (401, 403), f"code={code}")

    return results
