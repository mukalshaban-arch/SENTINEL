"""Tests for the map-pinning helpers in nlp.py: _ensure_hotspot and
_pin_location.

Both exist to stop re-committing a job (or a differently-worded mention of
the same place) from stacking duplicate pins and hotspots, so the de-dup
branches are the point of these tests. geopandas-based proximity matching is
stubbed here — it has its own tests in test_nlp.py.
"""
from contextlib import contextmanager

import pytest

import nlp


class ScriptedCursor:
    def __init__(self, fetchone_results=None):
        self.fetchone_results = list(fetchone_results or [])
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.fetchone_results.pop(0) if self.fetchone_results else None

    def sql_containing(self, needle):
        return [(s, p) for s, p in self.executed if needle in s]


@pytest.fixture
def scripted(monkeypatch):
    def _install(fetchone_results=None):
        cur = ScriptedCursor(fetchone_results)

        @contextmanager
        def _fake(commit: bool = False):
            yield cur

        monkeypatch.setattr(nlp, "db_cursor", _fake)
        return cur

    return _install


HIT = {"lat": -1.29, "lng": 36.82, "confidence": "high"}


# ── _ensure_hotspot ───────────────────────────────────────────────────────
def test_ensure_hotspot_creates_when_none_exists(scripted, monkeypatch):
    cur = scripted([None, {"id": 55}])          # name lookup miss, then INSERT
    monkeypatch.setattr(nlp, "_find_nearby_hotspot", lambda lat, lng: None)

    assert nlp._ensure_hotspot("Nairobi", "GENERAL", HIT, "a note") == 55
    params = cur.sql_containing("INSERT INTO hotspots")[0][1]
    assert params == ("Nairobi", "GENERAL", "MEDIUM", -1.29, 36.82, "a note")


def test_ensure_hotspot_skips_when_same_name_exists(scripted, monkeypatch):
    cur = scripted([{"id": 1}])                 # name lookup hit
    monkeypatch.setattr(nlp, "_find_nearby_hotspot", lambda lat, lng: None)

    assert nlp._ensure_hotspot("Nairobi", "GENERAL", HIT, None) is None
    assert not cur.sql_containing("INSERT INTO hotspots")


def test_ensure_hotspot_skips_when_a_nearby_one_exists(scripted, monkeypatch):
    cur = scripted([None])                      # different name...
    monkeypatch.setattr(nlp, "_find_nearby_hotspot", lambda lat, lng: 99)   # ...but same place

    assert nlp._ensure_hotspot("Apapa warehouse", "GENERAL", HIT, None) is None
    assert not cur.sql_containing("INSERT INTO hotspots")


def test_ensure_hotspot_checks_proximity_at_the_hit_coordinates(scripted, monkeypatch):
    seen = {}
    scripted([None, {"id": 55}])
    monkeypatch.setattr(nlp, "_find_nearby_hotspot",
                        lambda lat, lng: seen.update(lat=lat, lng=lng) or None)

    nlp._ensure_hotspot("Nairobi", "GENERAL", HIT, None)
    assert seen == {"lat": -1.29, "lng": 36.82}


# ── _pin_location ─────────────────────────────────────────────────────────
def test_pin_location_writes_a_pin_when_none_exists(scripted):
    cur = scripted([None])
    assert nlp._pin_location(11, HIT) is True

    params = cur.sql_containing("INSERT INTO location_coords")[0][1]
    assert params[:3] == (11, -1.29, 36.82)
    assert "auto-geocoded (high)" == params[3]


def test_pin_location_is_a_noop_when_already_pinned(scripted):
    cur = scripted([{"?column?": 1}])
    assert nlp._pin_location(11, HIT) is False
    assert not cur.sql_containing("INSERT INTO location_coords")


def test_pin_location_label_records_the_confidence(scripted):
    cur = scripted([None])
    nlp._pin_location(11, {"lat": 1.0, "lng": 2.0, "confidence": "medium"})
    assert "auto-geocoded (medium)" == cur.sql_containing("INSERT INTO location_coords")[0][1][3]
