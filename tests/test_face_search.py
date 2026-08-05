"""Face Search: endpoint reachability. A real image match test needs a
sample photo and is better covered manually (see tests/MANUAL_CHECKLIST.md)."""
from _lib import call


def run(ctx):
    results = []
    tok = ctx["admin_tok"]

    code, r = call("POST", "/api/face/search", tok, {"image": ""})
    results.append(("PASS" if code in (200, 400, 503) else "FAIL",
                     "face search endpoint reachable", f"code={code} body={r}"))
    return results
