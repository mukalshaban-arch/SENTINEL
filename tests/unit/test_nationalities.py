"""Unit tests for nationalities.py: demonym -> country resolution and
country-name validation. Pure functions, zero dependencies — exhaustive
coverage is cheap and worthwhile since this logic gates what's allowed to
appear as a "country" anywhere in the system (Country Profiles, Link
Analysis country nodes, relationships)."""
import pytest

import nationalities as nat


def test_country_for_nationality_known_demonym():
    assert nat.country_for_nationality("Kenyan") == "Kenya"
    assert nat.country_for_nationality("kenyan") == "Kenya"
    assert nat.country_for_nationality("  Kenyan  ") == "Kenya"


def test_country_for_nationality_unknown_falls_back_to_title_case():
    assert nat.country_for_nationality("Wakandan") == "Wakandan"


def test_country_for_nationality_empty_input():
    assert nat.country_for_nationality("") == ""
    assert nat.country_for_nationality(None) == ""


def test_canonical_country_name_matches_case_insensitively():
    assert nat.canonical_country_name("kenya") == "Kenya"
    assert nat.canonical_country_name("KENYA") == "Kenya"
    assert nat.canonical_country_name(" Kenya ") == "Kenya"


def test_canonical_country_name_handles_multiword_names_with_connectors():
    # Regression case: naive str.title() breaks "of the" -> "Of The".
    assert nat.canonical_country_name("democratic republic of the congo") == \
        "Democratic Republic of the Congo"


def test_canonical_country_name_rejects_unknown():
    assert nat.canonical_country_name("Nowhereistan") is None
    assert nat.canonical_country_name("") is None
    assert nat.canonical_country_name(None) is None


def test_resolve_known_country_from_demonym():
    assert nat.resolve_known_country("Nigerian") == "Nigeria"


def test_resolve_known_country_from_country_name_directly():
    assert nat.resolve_known_country("Nigeria") == "Nigeria"


def test_resolve_known_country_rejects_garbage():
    assert nat.resolve_known_country("Nowhereistan") is None


def test_nationalities_for_country_filters_correctly():
    known = ["Kenyan", "Nigerian", "kenyan", "American", "Wakandan"]
    result = nat.nationalities_for_country("Kenya", known)
    assert set(result) == {"Kenyan", "kenyan"}


def test_nationalities_for_country_no_matches():
    assert nat.nationalities_for_country("Kenya", ["Nigerian", "American"]) == []


def test_known_countries_set_matches_demonym_values():
    assert nat.KNOWN_COUNTRIES == set(nat.DEMONYM_TO_COUNTRY.values())


def test_every_demonym_resolves_to_a_canonical_country_name():
    # Every value in the table must itself be a recognised canonical name —
    # guards against a future typo introducing an entry that can never be
    # validated back (canonical_country_name would silently reject it).
    for demonym, country in nat.DEMONYM_TO_COUNTRY.items():
        assert nat.canonical_country_name(country) == country, \
            f"{demonym!r} maps to {country!r}, which doesn't round-trip"
