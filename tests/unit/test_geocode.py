"""Unit tests for geocode.py: text normalization (must match the loader's
search_key format) and the geocode() resolution flow against a mocked
gazetteer table — no real DB or gazetteer data required."""
import pytest

import geocode


# ── _normalize ───────────────────────────────────────────────────────────
def test_normalize_lowercases():
    assert geocode._normalize("Nairobi") == "nairobi"


def test_normalize_strips_accents():
    assert geocode._normalize("Zürich") == "zurich"
    assert geocode._normalize("São Paulo") == "sao paulo"


def test_normalize_collapses_whitespace():
    assert geocode._normalize("  New   York  ") == "new york"


def test_normalize_empty_input():
    assert geocode._normalize("") == ""
    assert geocode._normalize(None) == ""


# ── geocode() ────────────────────────────────────────────────────────────
def test_geocode_returns_none_for_empty_name():
    assert geocode.geocode("") is None
    assert geocode.geocode(None) is None


def test_geocode_direct_match_medium_confidence(fake_db_cursor):
    fake_db_cursor.fetchone.return_value = {
        "lat": -1.29, "lng": 36.82, "name": "Nairobi", "country": "Kenya", "population": 4000000,
    }
    result = geocode.geocode("Nairobi")
    assert result == {
        "lat": -1.29, "lng": 36.82, "confidence": "medium",
        "matched_name": "Nairobi", "country": "Kenya",
    }


def test_geocode_with_country_hint_high_confidence(fake_db_cursor):
    fake_db_cursor.fetchone.return_value = {
        "lat": -1.29, "lng": 36.82, "name": "Nairobi", "country": "Kenya", "population": 4000000,
    }
    result = geocode.geocode("Nairobi", country="Kenya")
    assert result["confidence"] == "high"


def test_geocode_falls_back_to_address_first_segment(fake_db_cursor):
    # Direct name lookup misses (1 call), then the address-derived fallback
    # is tried — geocode()'s `_lookup(first, country) or _lookup(first, None)`
    # re-queries once more when country is None, so the 3rd call is the hit.
    fake_db_cursor.fetchone.side_effect = [
        None,  # _lookup(key, None) — direct name miss
        None,  # _lookup(first, None) — address-derived, 1st attempt
        {"lat": 1.0, "lng": 2.0, "name": "Lagos", "country": "Nigeria", "population": 100},
    ]
    result = geocode.geocode("Unresolvable Place", address="Lagos, Nigeria")
    assert result["matched_name"] == "Lagos"


def test_geocode_returns_none_when_nothing_matches(fake_db_cursor):
    fake_db_cursor.fetchone.return_value = None
    assert geocode.geocode("Nowhereville") is None


def test_geocode_never_raises_on_db_error(fake_db_cursor):
    fake_db_cursor.execute.side_effect = Exception("gazetteer table missing")
    assert geocode.geocode("Nairobi") is None
