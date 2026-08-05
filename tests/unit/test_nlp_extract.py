"""Unit tests for nlp_extract.py's pure helper functions. The spaCy-backed
extract_entities()/_extract() pipeline itself needs a real model download and
is exercised in tests/integration/test_nlp.py instead — importing this
module here never triggers that (spaCy is lazy-loaded inside _get_spacy())."""
import pytest

import nlp_extract as ne


# ── _norm ────────────────────────────────────────────────────────────────
def test_norm_collapses_whitespace():
    assert ne._norm("  hello   world  ") == "hello world"


def test_norm_handles_none_and_empty():
    assert ne._norm(None) == ""
    assert ne._norm("") == ""


# ── _pick_type ───────────────────────────────────────────────────────────
KEYWORD_TABLE = [
    ("MEETING", ["met", "meeting", "gathered"]),
    ("TRAVEL", ["flew", "travelled", "arrived"]),
]


def test_pick_type_matches_first_hit():
    assert ne._pick_type("they met at the cafe", KEYWORD_TABLE, "OTHER") == "MEETING"


def test_pick_type_matches_second_category():
    assert ne._pick_type("he flew to nairobi", KEYWORD_TABLE, "OTHER") == "TRAVEL"


def test_pick_type_falls_back_to_default_when_no_keyword_matches():
    assert ne._pick_type("nothing relevant here", KEYWORD_TABLE, "OTHER") == "OTHER"


def test_pick_type_respects_table_order_on_multiple_matches():
    # "met" (MEETING) and "arrived" (TRAVEL) both present — first table entry wins.
    assert ne._pick_type("they met after he arrived", KEYWORD_TABLE, "OTHER") == "MEETING"


# ── _parse_date ──────────────────────────────────────────────────────────
def test_parse_date_iso_format():
    assert ne._parse_date("2024-05-05") == "2024-05-05"


def test_parse_date_natural_language():
    assert ne._parse_date("5 May 2024") == "2024-05-05"


def test_parse_date_unparseable_returns_none():
    assert ne._parse_date("not a date at all, just words") is None


def test_parse_date_default_fallback_year_not_fabricated():
    # dateutil silently defaults missing fields to 1900-01-01 when it can't
    # find a real date — that must surface as None, not a fake date.
    assert ne._parse_date("gibberish xyzzy plugh") is None


def test_parse_date_explicit_1900_is_preserved():
    assert ne._parse_date("1 January 1900") == "1900-01-01"
