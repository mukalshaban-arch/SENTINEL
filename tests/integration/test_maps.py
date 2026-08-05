"""Maps: local tile-serving endpoint responds (basemap imagery itself is
fetched by the browser from OpenFreeMap, not the server — see README's
Offline-by-design section)."""
from _lib import call


def run(ctx):
    results = []
    tok = ctx["admin_tok"]

    code, r = call("GET", "/tiles/3/4/4.png", tok, is_json=False)
    results.append(("PASS" if code == 200 else "FAIL", "tile endpoint responds", f"code={code}"))
    return results
