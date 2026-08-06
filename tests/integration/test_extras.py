"""Generic entity extras: tags, notes, custom fields, attachments, images,
known locations, relationships — the /api/{person|group|activity|location}/
:id/:resource family plus the /api/:resource/:id singleton mutate/delete.

These back the detail-page panels across the whole UI and were previously
untested end-to-end."""
from _lib import call

# A 1x1 transparent PNG — smallest valid image payload for upload paths.
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

    if not poi_id:
        check("extras suite prerequisites", False, "no poi_id from core entities")
        return results

    # ── Tags ─────────────────────────────────────────────────────────────
    code, r = call("POST", f"/api/person/{poi_id}/tags", tok, {"tag": "zz-surveillance", "color": "#ff0000"})
    check("add tag", code == 201 and "id" in r, f"code={code} body={r}")
    tag_id = r.get("id") if code == 201 else None

    code, r = call("GET", f"/api/person/{poi_id}/tags", tok)
    check("list tags", code == 200 and any(t["tag"] == "zz-surveillance" for t in r), f"code={code}")

    # Same tag again should upsert (ON CONFLICT DO UPDATE), not duplicate.
    code, r = call("POST", f"/api/person/{poi_id}/tags", tok, {"tag": "zz-surveillance", "color": "#00ff00"})
    check("duplicate tag upserts rather than duplicating", code == 201, f"code={code}")

    code, r = call("POST", f"/api/person/{poi_id}/tags", tok, {"tag": "   "})
    check("blank tag rejected", code == 400, f"code={code}")

    if tag_id:
        code, r = call("DELETE", f"/api/tags/{tag_id}", tok)
        check("delete tag", code == 200, f"code={code}")

    # ── Notes ────────────────────────────────────────────────────────────
    # note_type is constrained by schema.sql to
    # GENERAL/FIELD_REPORT/ASSESSMENT/OBSERVATION/WARNING.
    code, r = call("POST", f"/api/person/{poi_id}/notes", tok,
                    {"title": "ZZ Note", "body": "observed at market",
                     "noteType": "FIELD_REPORT", "isPinned": True})
    check("add note", code == 201 and "id" in r, f"code={code} body={r}")
    note_id = r.get("id") if code == 201 else None

    code, r = call("POST", f"/api/person/{poi_id}/notes", tok,
                    {"title": "ZZ Bad Type", "body": "x", "noteType": "NOT_A_VALID_TYPE"})
    check("invalid note_type rejected", code in (400, 500), f"code={code}")

    code, r = call("GET", f"/api/person/{poi_id}/notes", tok)
    check("list notes returns pinned first",
          code == 200 and len(r) >= 1 and r[0]["is_pinned"] is True, f"code={code}")

    if note_id:
        code, r = call("PUT", f"/api/notes/{note_id}", tok, {"title": "ZZ Note Edited", "isPinned": False})
        check("update note", code == 200, f"code={code}")

        code, r = call("GET", f"/api/person/{poi_id}/notes", tok)
        edited = next((n for n in r if n["id"] == note_id), None) if code == 200 else None
        check("note update round-trips", edited is not None and edited["title"] == "ZZ Note Edited")

        code, r = call("DELETE", f"/api/notes/{note_id}", tok)
        check("delete note", code == 200, f"code={code}")

    # ── Custom fields ────────────────────────────────────────────────────
    code, r = call("POST", f"/api/person/{poi_id}/fields", tok,
                    {"key": "zz_passport", "value": "X1234567", "fieldType": "TEXT"})
    check("add custom field", code == 201 and "id" in r, f"code={code} body={r}")
    field_id = r.get("id") if code == 201 else None

    code, r = call("GET", f"/api/person/{poi_id}/fields", tok)
    check("list custom fields", code == 200 and any(f["field_key"] == "zz_passport" for f in r), f"code={code}")

    code, r = call("POST", f"/api/person/{poi_id}/fields", tok, {"value": "no key"})
    check("custom field without key rejected", code == 400, f"code={code}")

    if field_id:
        code, r = call("PUT", f"/api/fields/{field_id}", tok, {"value": "Y7654321"})
        check("update custom field value", code == 200, f"code={code}")

        code, r = call("DELETE", f"/api/fields/{field_id}", tok)
        check("delete custom field", code == 200, f"code={code}")

    # ── Attachments ──────────────────────────────────────────────────────
    code, r = call("POST", f"/api/person/{poi_id}/attachments", tok,
                    {"name": "ZZ Report.txt", "attachType": "TEXT", "content": "classified body text",
                     "description": "test attachment"})
    check("add attachment", code == 201 and "id" in r, f"code={code} body={r}")
    attach_id = r.get("id") if code == 201 else None

    code, r = call("GET", f"/api/person/{poi_id}/attachments", tok)
    check("list attachments computes size", code == 200 and any(a["size_bytes"] > 0 for a in r), f"code={code}")

    code, r = call("POST", f"/api/person/{poi_id}/attachments", tok, {"content": "no name"})
    check("attachment without name rejected", code == 400, f"code={code}")

    if attach_id:
        code, r = call("DELETE", f"/api/attachments/{attach_id}", tok)
        check("delete attachment", code == 200, f"code={code}")

    # ── Images (also exercises the face-embedding hook on person images) ──
    code, r = call("POST", f"/api/person/{poi_id}/images", tok,
                    {"content": TINY_PNG, "name": "zz.png", "caption": "test", "mimeType": "image/png"})
    check("add image to person", code == 201 and "id" in r, f"code={code} body={r}")
    image_id = r.get("id") if code == 201 else None

    code, r = call("GET", f"/api/person/{poi_id}/images", tok)
    check("list images", code == 200 and isinstance(r, list) and len(r) >= 1, f"code={code}")

    code, r = call("POST", f"/api/person/{poi_id}/images", tok, {"name": "no content"})
    check("image without content rejected", code == 400, f"code={code}")

    if image_id:
        code, r = call("DELETE", f"/api/images/{image_id}", tok)
        check("delete image", code == 200, f"code={code}")

    # ── Known locations ──────────────────────────────────────────────────
    code, r = call("POST", f"/api/person/{poi_id}/locations", tok,
                    {"lat": -1.28, "lng": 36.81, "label": "ZZ Safehouse", "note": "observed twice",
                     "dateObserved": "2024-03-01"})
    check("add known location", code == 201 and "id" in r, f"code={code} body={r}")
    loc_id = r.get("id") if code == 201 else None

    code, r = call("GET", f"/api/person/{poi_id}/locations", tok)
    check("list known locations", code == 200 and any(l["label"] == "ZZ Safehouse" for l in r), f"code={code}")

    code, r = call("POST", f"/api/person/{poi_id}/locations", tok, {"label": "no coords"})
    check("location without lat/lng rejected", code == 400, f"code={code}")

    if loc_id:
        code, r = call("DELETE", f"/api/locations/{loc_id}", tok)
        check("delete known location", code == 200, f"code={code}")

    # ── Relationships ────────────────────────────────────────────────────
    if group_id:
        code, r = call("POST", f"/api/person/{poi_id}/relationships", tok,
                        {"relatedType": "group", "relatedId": group_id, "relType": "member of"})
        check("add person->group relationship", code == 201 and "id" in r, f"code={code} body={r}")
        rel_id = r.get("id") if code == 201 else None

        code, r = call("GET", f"/api/person/{poi_id}/relationships", tok)
        check("list relationships", code == 200 and isinstance(r, list) and len(r) >= 1, f"code={code}")

        if rel_id:
            code, r = call("DELETE", f"/api/relationships/{rel_id}", tok)
            check("delete relationship", code == 200, f"code={code}")

    # Country relationships are validated against the real-country list.
    code, r = call("POST", f"/api/person/{poi_id}/relationships", tok,
                    {"relatedType": "country", "relatedName": "Nowhereistan", "relType": "linked to"})
    check("relationship to fake country rejected", code == 400, f"code={code}")

    # ── Extras on other entity types ─────────────────────────────────────
    if group_id:
        code, r = call("POST", f"/api/group/{group_id}/notes", tok, {"title": "ZZ Group Note", "body": "x"})
        check("extras work on groups too", code == 201, f"code={code}")
        if code == 201:
            call("DELETE", f"/api/notes/{r.get('id')}", tok)

    if ctx.get("activity_id"):
        code, r = call("POST", f"/api/activity/{ctx['activity_id']}/tags", tok, {"tag": "zz-activity-tag"})
        check("extras work on activities too", code == 201, f"code={code}")
        if code == 201:
            call("DELETE", f"/api/tags/{r.get('id')}", tok)

    # ── Unknown resource / method handling ───────────────────────────────
    code, r = call("GET", f"/api/person/{poi_id}/nonexistentresource", tok)
    check("unknown extras resource 404s", code == 404, f"code={code}")

    return results
