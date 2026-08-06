"""Real spaCy-backed extraction tests for nlp_extract.py.

These need the en_core_web_sm model (~12MB — installed in CI by the
workflow). If it isn't present the whole module skips rather than fails, so
a developer without the model can still run the rest of the unit suite.

Assertions are deliberately tolerant about *which* entities the small model
finds — its recall on unusual names is a documented limitation (see the
module docstring in nlp_extract.py). What's asserted is the contract the
rest of the pipeline depends on: shape, types, de-duplication, metadata
stripping, and the enrichment rules layered on top of NER.
"""
import pytest

import nlp_extract as ne

spacy = pytest.importorskip("spacy", reason="spaCy not installed")

pytestmark = pytest.mark.skipif(
    not ne._get_spacy(),
    reason="en_core_web_sm not installed — run: python -m spacy download en_core_web_sm",
)

REPORT = """\
On 5 May 2024, Kenyan national Peter Mwangi met with members of the Haraka
Network in Nairobi. Mwangi, also known as "The Broker", wired funds to an
account in Lagos on 12 June 2024. Police in Mombasa monitored the transfer.
"""


# ── Output contract ───────────────────────────────────────────────────────
def test_extract_entities_returns_all_expected_keys():
    result = ne.extract_entities(REPORT)
    assert set(result) == {"persons", "groups", "locations", "activities", "image_links"}
    assert all(isinstance(v, list) for v in result.values())


def test_extract_entities_person_records_have_expected_fields():
    result = ne.extract_entities(REPORT)
    for p in result["persons"]:
        assert set(p) >= {"name", "aliases", "nationality", "notes"}
        # `aliases` is a single string (or None), not a list — nlp.commit_job
        # only reads name/nationality/notes, so nothing downstream depends on
        # it being a collection. Asserted here to pin the actual contract.
        assert p["aliases"] is None or isinstance(p["aliases"], str)
        assert isinstance(p["name"], str) and p["name"]


def test_extract_entities_location_records_have_expected_fields():
    result = ne.extract_entities(REPORT)
    for loc in result["locations"]:
        assert set(loc) >= {"name", "address", "country", "type", "notes"}


def test_extract_entities_activity_records_have_expected_fields():
    result = ne.extract_entities(REPORT)
    for act in result["activities"]:
        assert set(act) >= {"title", "type", "date", "notes",
                             "poi_names", "group_names", "location_name"}
        assert act["type"] in ne.ACTIVITY_TYPES


def test_extract_entities_finds_locations_in_a_clear_report():
    result = ne.extract_entities(REPORT)
    names = {loc["name"].lower() for loc in result["locations"]}
    # Nairobi/Lagos/Mombasa are unambiguous GPEs — at least one must land.
    assert names & {"nairobi", "lagos", "mombasa"}


def test_extract_entities_deduplicates_repeated_mentions():
    text = "Peter Mwangi met John Doe. Peter Mwangi left. Peter Mwangi returned."
    result = ne.extract_entities(text)
    names = [p["name"].lower() for p in result["persons"]]
    assert len(names) == len(set(names))


def test_extract_entities_empty_text_returns_empty_lists():
    result = ne.extract_entities("")
    assert result == {"persons": [], "groups": [], "locations": [],
                      "activities": [], "image_links": []}


def test_extract_entities_never_raises_on_garbage():
    for junk in ("...", "\x00\x01\x02", "?!?!?!", "a" * 2000):
        result = ne.extract_entities(junk)
        assert isinstance(result, dict)


# ── Nationality enrichment (demonym -> country) ──────────────────────────
def test_nationality_enrichment_resolves_demonym():
    result = ne.extract_entities("Kenyan national Peter Mwangi travelled to Lagos on 1 March 2024.")
    nats = {p.get("nationality") for p in result["persons"] if p.get("nationality")}
    if nats:  # only assert the mapping when the model tagged the NORP
        assert "Kenya" in nats or "Kenyan" in nats


# ── Metadata-line stripping ──────────────────────────────────────────────
def test_metadata_lines_are_stripped_before_ner():
    stripped = ne._strip_metadata_lines("Analyst: Jane Doe\nPeter Mwangi met the group in Nairobi.")
    assert "Jane Doe" not in stripped
    assert "Peter Mwangi" in stripped


def test_strip_metadata_lines_keeps_ordinary_prose():
    text = "Peter Mwangi met the group in Nairobi.\nHe left the following day."
    assert ne._strip_metadata_lines(text) == text


def test_analyst_byline_person_not_reported_as_subject():
    result = ne.extract_entities("Analyst: Jane Doe\nPeter Mwangi met contacts in Nairobi on 3 May 2024.")
    names = {p["name"].lower() for p in result["persons"]}
    assert "jane doe" not in names


# ── Org stoplist ─────────────────────────────────────────────────────────
def test_generic_institutions_are_not_reported_as_groups():
    result = ne.extract_entities("The UN and the police met in Nairobi on 4 April 2024.")
    names = {g["name"].lower() for g in result["groups"]}
    assert "un" not in names
    assert "police" not in names


# ── Activity typing ──────────────────────────────────────────────────────
@pytest.mark.parametrize("sentence,expected", [
    ("Peter Mwangi met his contact in Nairobi on 2 May 2024.", "MEETING"),
    ("Peter Mwangi wired funds to Lagos on 2 May 2024.", "FINANCIAL"),
    ("Peter Mwangi travelled to Mombasa on 2 May 2024.", "MOVEMENT"),
    ("Peter Mwangi phoned his associate in Nairobi on 2 May 2024.", "COMMUNICATION"),
])
def test_activity_type_is_inferred_from_verbs(sentence, expected):
    result = ne.extract_entities(sentence)
    if result["activities"]:
        assert any(a["type"] == expected for a in result["activities"])


def test_activity_dates_are_iso_formatted():
    result = ne.extract_entities(REPORT)
    for act in result["activities"]:
        if act.get("date"):
            assert len(act["date"]) == 10 and act["date"][4] == "-"


# ── match_images_to_entities ─────────────────────────────────────────────
# ocr_image is imported inside the function, so patching the module attribute
# takes effect at call time — and keeps the real OCR engine out of the test.
IMG = [{"filename": "p1.jpg", "saved_as": "abc.jpg", "mime": "image/jpeg", "path": "x"}]
ENTITIES = {"persons": [{"name": "Peter Mwangi"}], "groups": [{"name": "Haraka Network"}],
            "locations": [{"name": "Nairobi"}], "activities": [], "image_links": []}


def _patch_ocr(monkeypatch, text):
    import ocr_offline
    monkeypatch.setattr(ocr_offline, "ocr_image", lambda path: text)


def test_match_images_links_when_name_appears_in_ocr_text(monkeypatch):
    _patch_ocr(monkeypatch, "ID CARD — Peter Mwangi — Nairobi")
    links = ne.match_images_to_entities(IMG, ENTITIES)
    names = {l["entity_name"] for l in links}
    assert "Peter Mwangi" in names
    assert all(l["filename"] == "p1.jpg" for l in links)
    assert all(l["confidence"] == "medium" for l in links)


def test_match_images_returns_nothing_when_no_name_matches(monkeypatch):
    _patch_ocr(monkeypatch, "completely unrelated text")
    assert ne.match_images_to_entities(IMG, ENTITIES) == []


def test_match_images_ignores_ocr_placeholder_output(monkeypatch):
    # ocr_offline returns "[...]" placeholders when no engine is available.
    _patch_ocr(monkeypatch, "[Image — no OCR text]")
    assert ne.match_images_to_entities(IMG, ENTITIES) == []


def test_match_images_survives_ocr_failure(monkeypatch):
    import ocr_offline

    def boom(path):
        raise RuntimeError("ocr exploded")

    monkeypatch.setattr(ocr_offline, "ocr_image", boom)
    assert ne.match_images_to_entities(IMG, ENTITIES) == []


def test_match_images_empty_input():
    assert ne.match_images_to_entities([], ENTITIES) == []


def test_match_images_no_candidate_entities():
    empty = {"persons": [], "groups": [], "locations": [], "activities": [], "image_links": []}
    assert ne.match_images_to_entities(IMG, empty) == []
