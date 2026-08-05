"""NLP / Analysis pipeline: submit -> poll -> reviewed, using the real
offline spaCy pipeline (no mocking — this exercises actual model inference)."""
import time
from _lib import call


def run(ctx):
    results = []
    tok = ctx["admin_tok"]

    def check(name, cond, detail=""):
        results.append(("PASS" if cond else "FAIL", name, detail))

    code, r = call("POST", "/api/nlp/submit", tok,
                    {"text": "On 5 May 2024, Kenyan national ZZTest Suspect met with "
                             "ZZTest Faction in Nairobi."})
    check("nlp submit", code == 202 and "job_id" in r, f"code={code} body={r}")
    job_id = r.get("job_id") if code == 202 else None

    status = None
    if job_id:
        for _ in range(15):
            time.sleep(2)
            code, r = call("GET", f"/api/nlp/jobs/{job_id}", tok)
            status = r.get("status")
            if status in ("reviewed", "failed"):
                break
    check("nlp job reaches reviewed", status == "reviewed", f"final status={status}")

    if status == "reviewed":
        code, r = call("POST", f"/api/nlp/jobs/{job_id}/reject", tok, {})
        check("nlp job reject (cleanup, not committing test data)", code == 200, f"code={code}")

    code, r = call("GET", "/api/nlp/jobs", tok)
    check("nlp job list", code == 200 and isinstance(r, list), f"code={code}")

    return results
