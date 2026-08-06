"""Comprehensive backend test suite for SENTINEL. Exercises every module
against a live server with real writes, cleaned up afterward. Stdlib only.

Usage:
    venv\\Scripts\\python.exe tests\\run_all.py

Requires the server already running (server.py) on SENTINEL_PORT (default
8090) — this hits the real HTTP API, not the code directly, so it catches
routing/auth/serialization bugs a unit test would miss.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib import server_reachable, BASE  # noqa: E402

import test_auth
import test_core_entities
import test_detail_views
import test_extras
import test_country_profiles
import test_link_analysis
import test_nlp
import test_summaries_and_nlp_commit
import test_face_search
import test_role_enforcement
import test_admin
import test_errors_and_search
import test_maps
import cleanup

MODULES = [
    ("AUTH", test_auth),
    ("CORE ENTITIES", test_core_entities),
    ("DETAIL VIEWS", test_detail_views),
    ("ENTITY EXTRAS", test_extras),
    ("COUNTRY PROFILES", test_country_profiles),
    ("LINK ANALYSIS", test_link_analysis),
    ("NLP / ANALYSIS", test_nlp),
    ("SUMMARIES & NLP COMMIT", test_summaries_and_nlp_commit),
    ("FACE SEARCH", test_face_search),
    ("ROLE ENFORCEMENT", test_role_enforcement),
    ("ADMIN", test_admin),
    ("ERRORS & SEARCH", test_errors_and_search),
    ("MAPS", test_maps),
]


def main():
    if not server_reachable():
        print(f"Cannot reach server at {BASE}. Start it first:")
        print(r'  venv\Scripts\python.exe server.py')
        sys.exit(2)

    ctx = {}
    all_results = []

    for label, module in MODULES:
        print(f"\n=== {label} ===")
        try:
            results = module.run(ctx)
        except Exception as e:
            results = [("FAIL", f"{label} module raised an exception", repr(e))]
        for status, name, detail in results:
            print(f"[{status}] {name}" + (f" — {detail}" if detail and status == "FAIL" else ""))
        all_results.extend(results)

        if label == "AUTH" and not ctx.get("admin_tok"):
            print("\nCannot continue without an admin token.")
            break

    print("\n=== CLEANUP ===")
    try:
        cleanup.run(ctx)
        print("cleaned up ZZTest/ZZFail test records")
    except Exception as e:
        print(f"cleanup raised an exception (non-fatal): {e!r}")

    passed = sum(1 for s, _, _ in all_results if s == "PASS")
    failed = sum(1 for s, _, _ in all_results if s == "FAIL")
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed (of {len(all_results)})")
    if failed:
        print("\nFAILED CHECKS:")
        for s, name, detail in all_results:
            if s == "FAIL":
                print(f"  - {name}: {detail}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
