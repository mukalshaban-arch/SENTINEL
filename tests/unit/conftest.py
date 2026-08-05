"""Shared fixtures for the unit suite. No live DB, no live server, no ML
models — everything here runs in a plain GitHub Actions runner in seconds.

Modules under test lazy-load their heavy ML dependencies (spaCy, PaddleOCR/
EasyOCR, InsightFace) inside functions, not at import time, so importing
server.py / nlp.py / nlp_extract.py / ocr_offline.py / face_match.py here
never touches those. Only lightweight deps are required (see
requirements-test.txt): psycopg2-binary, bcrypt, numpy, python-dateutil.
"""
import os
import sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# auth._jwt_secret() requires this to be set (min 32 chars) before any
# token is issued/verified. Set once, up front, for the whole run.
os.environ.setdefault("SENTINEL_JWT_SECRET", "unit-test-secret-key-not-for-production-use-0000")


@pytest.fixture
def fake_db_cursor(monkeypatch):
    """Patches db.db_cursor (and every module that already imported it by
    name, e.g. `from db import db_cursor`) with a context manager yielding a
    MagicMock cursor. The test configures cursor.execute / .fetchone /
    .fetchall via the returned mock; nothing touches a real database.

    Usage:
        def test_x(fake_db_cursor):
            fake_db_cursor.fetchone.return_value = {"lat": 1, "lng": 2, ...}
            ...
    """
    cursor = MagicMock()

    @contextmanager
    def _fake_db_cursor(commit: bool = False):
        yield cursor

    import db
    monkeypatch.setattr(db, "db_cursor", _fake_db_cursor)
    # Modules that did `from db import db_cursor` hold their own reference —
    # patch those too so the fake actually gets used wherever it's called.
    for modname in ("geocode", "auth", "face_match", "server"):
        mod = sys.modules.get(modname)
        if mod is not None and hasattr(mod, "db_cursor"):
            monkeypatch.setattr(mod, "db_cursor", _fake_db_cursor)

    return cursor
