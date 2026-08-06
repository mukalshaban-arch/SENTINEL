"""Two remaining server paths the other suites don't reach:

1. AI narrative summary generation — builds the full person/group dossier
   (a large read path) before calling the model. Without an API key the
   endpoint must fail as a clean 503, not a 500, and the dossier code still
   runs, which is the point of exercising it here.
2. The NLP commit path — the other NLP test rejects its job, so nothing ever
   drives nlp.commit_job through the API. This submits a job and commits it,
   then cleans up whatever it created.
"""
import time

from _lib import call


def run(ctx):
    results = []
    tok = ctx["admin_tok"]
    analyst_tok = ctx["analyst_tok"]
    viewer_tok = ctx["viewer_tok"]
    poi_id = ctx.get("poi_id")
    group_id = ctx.get("group_id")

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    # ── Summary generation ───────────────────────────────────────────────
    # Either the model backend is configured (200) or it isn't (503). Both
    # are correct; a 500 is not. The dossier build runs either way.
    if poi_id:
        code, r = call("POST", f"/api/persons/{poi_id}/summary", analyst_tok, {})
        check("generate person summary returns 200 or clean 503",
              code in (200, 503), f"code={code} body={r}")
        if code == 200:
            check("generated person summary is stored and returned",
                  bool(r.get("summary")), f"body={r}")
            code, r = call("GET", f"/api/persons/{poi_id}/summary", tok)
            check("stored person summary is retrievable", code == 200 and r.get("summary"))

    if group_id:
        code, r = call("POST", f"/api/groups/{group_id}/summary", analyst_tok, {})
        check("generate group summary returns 200 or clean 503",
              code in (200, 503), f"code={code} body={r}")

    code, r = call("POST", "/api/persons/99999999/summary", analyst_tok, {})
    check("summary for missing person 404s", code == 404, f"code={code}")

    code, r = call("POST", "/api/groups/99999999/summary", analyst_tok, {})
    check("summary for missing group 404s", code == 404, f"code={code}")

    if poi_id:
        code, r = call("POST", f"/api/persons/{poi_id}/summary", viewer_tok, {})
        check("viewer cannot generate summaries", code in (401, 403), f"code={code}")

    # ── Link chart node update / delete ──────────────────────────────────
    chart_id = ctx.get("chart_id")
    if chart_id and poi_id:
        code, r = call("POST", f"/api/link-charts/{chart_id}/nodes", tok,
                        {"nodeType": "country", "nodeRef": "Nigeria", "x": 5, "y": 5})
        node_id = r.get("id") if code == 201 else None
        check("add a second country node", code == 201, f"code={code} body={r}")

        if node_id:
            code, r = call("PUT", f"/api/link-charts/{chart_id}/nodes/{node_id}", tok,
                            {"x": 250, "y": 175})
            check("update node position (drag persistence)", code == 200, f"code={code}")

            code, r = call("GET", f"/api/link-charts/{chart_id}", tok)
            moved = next((n for n in r.get("nodes", []) if n["id"] == node_id), None) if code == 200 else None
            check("node position round-trips", moved is not None and moved["x"] == 250)

            code, r = call("DELETE", f"/api/link-charts/{chart_id}/nodes/{node_id}", tok)
            check("delete node from chart", code == 200, f"code={code}")

        code, r = call("POST", f"/api/link-charts/{chart_id}/nodes", viewer_tok,
                        {"nodeType": "country", "nodeRef": "Ghana"})
        check("viewer cannot add chart nodes", code in (401, 403), f"code={code}")

    # ── NLP commit ───────────────────────────────────────────────────────
    code, r = call("POST", "/api/nlp/submit", analyst_tok,
                    {"text": "On 7 July 2024, ZZCommit Suspect met ZZCommit Faction in Nairobi."})
    check("nlp submit for commit test", code == 202, f"code={code} body={r}")
    job_id = r.get("job_id") if code == 202 else None

    status = None
    if job_id:
        for _ in range(15):
            time.sleep(2)
            code, r = call("GET", f"/api/nlp/jobs/{job_id}", tok)
            status = r.get("status")
            if status in ("reviewed", "failed"):
                break
    check("nlp job for commit reaches reviewed", status == "reviewed", f"status={status}")

    if status == "reviewed":
        code, r = call("GET", f"/api/nlp/jobs/{job_id}", tok)
        output = r.get("claude_output") or {} if code == 200 else {}

        # Commit with explicit empty selections: drives commit_job and its
        # status transition without writing entities we'd then have to hunt
        # down and delete. Extraction quality varies by model, so committing
        # everything would make cleanup non-deterministic.
        code, r = call("POST", f"/api/nlp/jobs/{job_id}/commit", analyst_tok,
                        {"selections": {"persons": [], "groups": [],
                                        "locations": [], "activities": []}})
        check("nlp commit with empty selections succeeds", code == 200 and r.get("ok") is True,
              f"code={code} body={r}")
        check("commit returns a summary of what was written",
              isinstance(r.get("summary"), dict), f"body={r}")

        code, r = call("GET", f"/api/nlp/jobs/{job_id}", tok)
        check("committed job status is 'committed'", r.get("status") == "committed",
              f"status={r.get('status')}")

        # Re-committing an already-committed job must fail cleanly (404 —
        # commit_job only accepts jobs still in 'reviewed').
        code, r = call("POST", f"/api/nlp/jobs/{job_id}/commit", analyst_tok, {})
        check("re-committing a committed job is rejected", code == 404, f"code={code}")

    code, r = call("POST", "/api/nlp/jobs/999999/commit", analyst_tok, {})
    check("committing an unknown job 404s", code == 404, f"code={code}")

    code, r = call("POST", "/api/nlp/jobs/999999/reject", viewer_tok, {})
    check("viewer cannot reject nlp jobs", code in (401, 403), f"code={code}")

    return results
