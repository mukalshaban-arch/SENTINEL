"""Unit tests for nlp.commit_job — the step that writes analyst-approved
extracted entities into the database.

The DB is stubbed with a scripted cursor so each INSERT/SELECT can be given
a deterministic result. What's asserted is the orchestration: entity
insert-or-fetch, name->id resolution used to wire activities to their
person/group, coordinate inheritance from geocoded locations, image linking,
and the final job status transition.
"""
from contextlib import contextmanager

import pytest

import nlp


class ScriptedCursor:
    """A stand-in cursor. `fetchone` pops from a queue; every executed SQL
    statement is recorded so tests can assert on what was written."""

    def __init__(self, fetchone_results=None, fetchall_results=None):
        self.fetchone_results = list(fetchone_results or [])
        self.fetchall_results = list(fetchall_results or [])
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.fetchone_results.pop(0) if self.fetchone_results else None

    def fetchall(self):
        return self.fetchall_results.pop(0) if self.fetchall_results else []

    def sql_containing(self, needle):
        return [(s, p) for s, p in self.executed if needle in s]


@pytest.fixture
def scripted(monkeypatch):
    """Installs a ScriptedCursor as nlp.db_cursor and returns it."""
    def _install(fetchone_results=None):
        cur = ScriptedCursor(fetchone_results)

        @contextmanager
        def _fake(commit: bool = False):
            yield cur

        monkeypatch.setattr(nlp, "db_cursor", _fake)
        # Geocoding off unless a test turns it on — keeps the DB script short.
        monkeypatch.setattr(nlp, "geocode", lambda *a, **kw: None)
        return cur

    return _install


def _job(output):
    """The first fetchone in commit_job reads the job row."""
    return {"claude_output": output}


EMPTY = {"persons": [], "groups": [], "locations": [], "activities": [], "image_links": []}


# ── Job lookup ────────────────────────────────────────────────────────────
def test_commit_raises_when_job_missing_or_not_reviewed(scripted):
    scripted([None])
    with pytest.raises(ValueError, match="not found or not in reviewed state"):
        nlp.commit_job(1)


def test_commit_marks_job_committed(scripted):
    cur = scripted([_job(dict(EMPTY))])
    nlp.commit_job(1)
    committed = cur.sql_containing("status = 'committed'")
    assert committed and committed[0][1] == (1,)


def test_commit_returns_empty_summary_for_empty_output(scripted):
    scripted([_job(dict(EMPTY))])
    summary = nlp.commit_job(1)
    assert summary == {"persons": [], "groups": [], "locations": [],
                       "hotspots": [], "activities": [], "image_links": []}


# ── Persons ───────────────────────────────────────────────────────────────
def test_commit_inserts_a_person(scripted):
    data = dict(EMPTY, persons=[{"name": "Peter Mwangi", "nationality": "Kenya", "notes": "n"}])
    cur = scripted([_job(data), {"id": 42}])

    summary = nlp.commit_job(1)
    assert summary["persons"] == [{"name": "Peter Mwangi", "id": 42}]
    inserts = cur.sql_containing("INSERT INTO poi")
    assert inserts[0][1] == ("Peter Mwangi", "Kenya", "n")


def test_commit_reuses_existing_person_on_conflict(scripted):
    data = dict(EMPTY, persons=[{"name": "Existing"}])
    # INSERT ... ON CONFLICT DO NOTHING returns no row -> SELECT finds the id.
    cur = scripted([_job(data), None, {"id": 7}])

    summary = nlp.commit_job(1)
    assert summary["persons"] == [{"name": "Existing", "id": 7}]
    assert cur.sql_containing("SELECT id FROM poi WHERE alias")


def test_commit_skips_unnamed_persons(scripted):
    data = dict(EMPTY, persons=[{"name": "   "}, {"nationality": "Kenya"}])
    cur = scripted([_job(data)])
    assert nlp.commit_job(1)["persons"] == []
    assert not cur.sql_containing("INSERT INTO poi")


def test_commit_handles_person_that_can_be_neither_inserted_nor_found(scripted):
    data = dict(EMPTY, persons=[{"name": "Ghost"}])
    scripted([_job(data), None, None])
    assert nlp.commit_job(1)["persons"] == []


# ── Groups ────────────────────────────────────────────────────────────────
def test_commit_inserts_a_group(scripted):
    data = dict(EMPTY, groups=[{"name": "Haraka", "category": "NETWORK", "description": "d", "notes": "n"}])
    cur = scripted([_job(data), {"id": 5}])

    summary = nlp.commit_job(1)
    assert summary["groups"] == [{"name": "Haraka", "id": 5}]
    assert cur.sql_containing("INSERT INTO groups_of_interest")[0][1] == ("Haraka", "NETWORK", "d", "n")


def test_commit_reuses_existing_group(scripted):
    data = dict(EMPTY, groups=[{"name": "Haraka"}])
    cur = scripted([_job(data), None, {"id": 9}])
    assert nlp.commit_job(1)["groups"] == [{"name": "Haraka", "id": 9}]
    assert cur.sql_containing("SELECT id FROM groups_of_interest WHERE name")


def test_commit_skips_unnamed_groups(scripted):
    data = dict(EMPTY, groups=[{"name": ""}])
    cur = scripted([_job(data)])
    assert nlp.commit_job(1)["groups"] == []
    assert not cur.sql_containing("INSERT INTO groups_of_interest")


# ── Locations (no geocode hit) ───────────────────────────────────────────
def test_commit_inserts_a_location(scripted):
    data = dict(EMPTY, locations=[{"name": "Nairobi", "address": "a", "country": "Kenya", "notes": "n"}])
    cur = scripted([_job(data), {"id": 11}])

    summary = nlp.commit_job(1)
    assert summary["locations"] == [{"name": "Nairobi", "id": 11}]
    assert cur.sql_containing("INSERT INTO locations")[0][1] == ("Nairobi", "a", "Kenya", "n")


def test_commit_skips_unnamed_locations(scripted):
    data = dict(EMPTY, locations=[{"name": "  "}])
    cur = scripted([_job(data)])
    assert nlp.commit_job(1)["locations"] == []
    assert not cur.sql_containing("INSERT INTO locations")


def test_unresolvable_location_is_not_geocoded_or_pinned(scripted):
    data = dict(EMPTY, locations=[{"name": "Nowhereville"}])
    scripted([_job(data), {"id": 11}])
    summary = nlp.commit_job(1)
    assert "geocoded" not in summary["locations"][0]
    assert summary["hotspots"] == []


# ── Locations (with geocode hit) ─────────────────────────────────────────
HIT = {"lat": -1.29, "lng": 36.82, "confidence": "high", "matched_name": "Nairobi", "country": "Kenya"}


def test_geocoded_location_is_pinned_and_becomes_a_hotspot(scripted, monkeypatch):
    data = dict(EMPTY, locations=[{"name": "Nairobi", "type": "MEETING_POINT"}])
    cur = scripted([_job(data), {"id": 11}])
    monkeypatch.setattr(nlp, "geocode", lambda *a, **kw: HIT)
    monkeypatch.setattr(nlp, "_pin_location", lambda lid, hit: True)
    monkeypatch.setattr(nlp, "_ensure_hotspot", lambda name, htype, hit, note: 99)

    summary = nlp.commit_job(1)
    loc = summary["locations"][0]
    assert loc["geocoded"] == {"lat": -1.29, "lng": 36.82, "confidence": "high"}
    assert loc["hotspot_id"] == 99
    assert summary["hotspots"] == [{"name": "Nairobi", "id": 99}]


def test_geocoded_location_without_new_pin_still_reports_hotspot(scripted, monkeypatch):
    data = dict(EMPTY, locations=[{"name": "Nairobi"}])
    scripted([_job(data), {"id": 11}])
    monkeypatch.setattr(nlp, "geocode", lambda *a, **kw: HIT)
    monkeypatch.setattr(nlp, "_pin_location", lambda lid, hit: False)   # already pinned
    monkeypatch.setattr(nlp, "_ensure_hotspot", lambda *a: 99)

    summary = nlp.commit_job(1)
    assert "geocoded" not in summary["locations"][0]
    assert summary["locations"][0]["hotspot_id"] == 99


def test_hotspot_dedup_returning_none_is_tolerated(scripted, monkeypatch):
    data = dict(EMPTY, locations=[{"name": "Nairobi"}])
    scripted([_job(data), {"id": 11}])
    monkeypatch.setattr(nlp, "geocode", lambda *a, **kw: HIT)
    monkeypatch.setattr(nlp, "_pin_location", lambda lid, hit: True)
    monkeypatch.setattr(nlp, "_ensure_hotspot", lambda *a: None)

    summary = nlp.commit_job(1)
    assert summary["hotspots"] == []
    assert "hotspot_id" not in summary["locations"][0]


# ── Activities ────────────────────────────────────────────────────────────
def test_commit_inserts_an_activity(scripted):
    data = dict(EMPTY, activities=[{"title": "Meeting", "type": "MEETING", "date": "2024-05-05",
                                     "location_name": "Nairobi", "notes": "detail"}])
    cur = scripted([_job(data), {"id": 21}])

    summary = nlp.commit_job(1)
    assert summary["activities"] == [{"title": "Meeting", "id": 21}]
    params = cur.sql_containing("INSERT INTO activities")[0][1]
    assert params[2] == "MEETING"
    assert params[3] == "2024-05-05"
    assert params[7] == "Meeting\n\ndetail"     # notes appended to description


def test_activity_description_is_just_the_title_without_notes(scripted):
    data = dict(EMPTY, activities=[{"title": "Meeting"}])
    cur = scripted([_job(data), {"id": 21}])
    nlp.commit_job(1)
    assert cur.sql_containing("INSERT INTO activities")[0][1][7] == "Meeting"


def test_activity_type_is_normalised(scripted):
    data = dict(EMPTY, activities=[{"title": "X", "type": "not-a-type"}])
    cur = scripted([_job(data), {"id": 21}])
    nlp.commit_job(1)
    assert cur.sql_containing("INSERT INTO activities")[0][1][2] == "OTHER"


def test_blank_date_becomes_null(scripted):
    data = dict(EMPTY, activities=[{"title": "X", "date": ""}])
    cur = scripted([_job(data), {"id": 21}])
    nlp.commit_job(1)
    assert cur.sql_containing("INSERT INTO activities")[0][1][3] is None


def test_commit_skips_untitled_activities(scripted):
    data = dict(EMPTY, activities=[{"title": "  "}])
    cur = scripted([_job(data)])
    assert nlp.commit_job(1)["activities"] == []
    assert not cur.sql_containing("INSERT INTO activities")


def test_activity_is_linked_to_its_extracted_person_and_group(scripted):
    data = dict(EMPTY,
                persons=[{"name": "Peter"}],
                groups=[{"name": "Haraka"}],
                activities=[{"title": "Meeting", "poi_names": ["Peter"], "group_names": ["Haraka"]}])
    cur = scripted([_job(data), {"id": 1}, {"id": 2}, {"id": 21}])

    nlp.commit_job(1)
    params = cur.sql_containing("INSERT INTO activities")[0][1]
    assert params[0] == 1     # poi_id
    assert params[1] == 2     # group_id


def test_activity_ignores_unresolved_entity_names(scripted):
    data = dict(EMPTY, activities=[{"title": "Meeting", "poi_names": ["Nobody"],
                                     "group_names": ["Nothing"]}])
    cur = scripted([_job(data), {"id": 21}])
    nlp.commit_job(1)
    params = cur.sql_containing("INSERT INTO activities")[0][1]
    assert params[0] is None and params[1] is None


def test_activity_uses_first_resolvable_person(scripted):
    data = dict(EMPTY,
                persons=[{"name": "Second"}],
                activities=[{"title": "M", "poi_names": ["Unknown", "Second"]}])
    cur = scripted([_job(data), {"id": 3}, {"id": 21}])
    nlp.commit_job(1)
    assert cur.sql_containing("INSERT INTO activities")[0][1][0] == 3


def test_activity_inherits_coordinates_from_geocoded_location(scripted, monkeypatch):
    data = dict(EMPTY,
                locations=[{"name": "Nairobi"}],
                activities=[{"title": "Meeting", "location_name": "Nairobi"}])
    cur = scripted([_job(data), {"id": 11}, {"id": 21}])
    monkeypatch.setattr(nlp, "geocode", lambda *a, **kw: HIT)
    monkeypatch.setattr(nlp, "_pin_location", lambda lid, hit: True)
    monkeypatch.setattr(nlp, "_ensure_hotspot", lambda *a: None)

    nlp.commit_job(1)
    params = cur.sql_containing("INSERT INTO activities")[0][1]
    assert params[5] == -1.29 and params[6] == 36.82


def test_person_last_location_is_backfilled_from_activity(scripted, monkeypatch):
    data = dict(EMPTY,
                persons=[{"name": "Peter"}],
                locations=[{"name": "Nairobi"}],
                activities=[{"title": "M", "poi_names": ["Peter"], "location_name": "Nairobi"}])
    cur = scripted([_job(data), {"id": 1}, {"id": 11}, {"id": 21}])
    monkeypatch.setattr(nlp, "geocode", lambda *a, **kw: HIT)
    monkeypatch.setattr(nlp, "_pin_location", lambda lid, hit: True)
    monkeypatch.setattr(nlp, "_ensure_hotspot", lambda *a: None)

    nlp.commit_job(1)
    updates = cur.sql_containing("UPDATE poi SET last_lat")
    assert updates and updates[0][1] == (-1.29, 36.82, 1)
    # Must not clobber coordinates an analyst already plotted.
    assert "last_lat IS NULL" in updates[0][0]


def test_group_base_is_backfilled_from_activity(scripted, monkeypatch):
    data = dict(EMPTY,
                groups=[{"name": "Haraka"}],
                locations=[{"name": "Nairobi"}],
                activities=[{"title": "M", "group_names": ["Haraka"], "location_name": "Nairobi"}])
    cur = scripted([_job(data), {"id": 2}, {"id": 11}, {"id": 21}])
    monkeypatch.setattr(nlp, "geocode", lambda *a, **kw: HIT)
    monkeypatch.setattr(nlp, "_pin_location", lambda lid, hit: True)
    monkeypatch.setattr(nlp, "_ensure_hotspot", lambda *a: None)

    nlp.commit_job(1)
    updates = cur.sql_containing("UPDATE groups_of_interest SET base_lat")
    assert updates and updates[0][1] == (-1.29, 36.82, 2)
    assert "base_lat IS NULL" in updates[0][0]


# ── Image links ───────────────────────────────────────────────────────────
def _image_job(tmp_path, links, extra=None):
    img = tmp_path / "stored.jpg"
    img.write_bytes(b"\xff\xd8\xff-fake-jpeg")
    data = dict(EMPTY, image_links=links)
    data["_image_files"] = [{"filename": "photo.jpg", "saved_as": "stored.jpg", "mime": "image/jpeg"}]
    if extra:
        data.update(extra)
    return data, img


def test_image_link_is_stored_against_the_person(scripted, monkeypatch, tmp_path):
    data, _ = _image_job(tmp_path,
                         [{"entity_type": "poi", "entity_name": "Peter",
                           "filename": "photo.jpg", "reason": "name on ID card"}],
                         extra={"persons": [{"name": "Peter"}]})
    cur = scripted([_job(data), {"id": 1}, {"id": 77}])
    monkeypatch.setattr(nlp, "NLP_DIR", tmp_path)

    summary = nlp.commit_job(1)
    assert summary["image_links"] == [{"entity_type": "poi", "entity_name": "Peter",
                                       "filename": "photo.jpg", "image_id": 77}]
    params = cur.sql_containing("INSERT INTO images")[0][1]
    assert params[0] == "person"                      # mapped entity type
    assert params[2].startswith("data:image/jpeg;base64,")
    assert "Auto-linked by NLP: name on ID card" == params[4]


def test_image_link_skipped_for_unknown_entity_type(scripted, monkeypatch, tmp_path):
    data, _ = _image_job(tmp_path, [{"entity_type": "spaceship", "entity_name": "X",
                                     "filename": "photo.jpg"}])
    cur = scripted([_job(data)])
    monkeypatch.setattr(nlp, "NLP_DIR", tmp_path)
    assert nlp.commit_job(1)["image_links"] == []
    assert not cur.sql_containing("INSERT INTO images")


def test_image_link_skipped_when_filename_not_uploaded(scripted, monkeypatch, tmp_path):
    data, _ = _image_job(tmp_path, [{"entity_type": "poi", "entity_name": "Peter",
                                     "filename": "never-uploaded.jpg"}])
    cur = scripted([_job(data)])
    monkeypatch.setattr(nlp, "NLP_DIR", tmp_path)
    assert nlp.commit_job(1)["image_links"] == []
    assert not cur.sql_containing("INSERT INTO images")


def test_image_link_skipped_when_file_is_missing_on_disk(scripted, monkeypatch, tmp_path):
    data, img = _image_job(tmp_path,
                           [{"entity_type": "poi", "entity_name": "Peter", "filename": "photo.jpg"}],
                           extra={"persons": [{"name": "Peter"}]})
    img.unlink()
    cur = scripted([_job(data), {"id": 1}])
    monkeypatch.setattr(nlp, "NLP_DIR", tmp_path)
    assert nlp.commit_job(1)["image_links"] == []
    assert not cur.sql_containing("INSERT INTO images")


def test_image_link_falls_back_to_db_lookup_for_person(scripted, monkeypatch, tmp_path):
    """The named person wasn't part of this commit, so its id is looked up."""
    data, _ = _image_job(tmp_path, [{"entity_type": "poi", "entity_name": "Preexisting",
                                     "filename": "photo.jpg"}])
    cur = scripted([_job(data), {"id": 55}, {"id": 77}])
    monkeypatch.setattr(nlp, "NLP_DIR", tmp_path)

    summary = nlp.commit_job(1)
    assert cur.sql_containing("SELECT id FROM poi WHERE alias")
    assert summary["image_links"][0]["image_id"] == 77


def test_image_link_dropped_when_entity_cannot_be_resolved(scripted, monkeypatch, tmp_path):
    data, _ = _image_job(tmp_path, [{"entity_type": "poi", "entity_name": "Ghost",
                                     "filename": "photo.jpg"}])
    cur = scripted([_job(data), None])
    monkeypatch.setattr(nlp, "NLP_DIR", tmp_path)
    assert nlp.commit_job(1)["image_links"] == []
    assert not cur.sql_containing("INSERT INTO images")


def test_image_link_resolves_an_activity_by_title(scripted, monkeypatch, tmp_path):
    data, _ = _image_job(tmp_path,
                         [{"entity_type": "activity", "entity_name": "Meeting",
                           "filename": "photo.jpg"}],
                         extra={"activities": [{"title": "Meeting"}]})
    cur = scripted([_job(data), {"id": 21}, {"id": 77}])
    monkeypatch.setattr(nlp, "NLP_DIR", tmp_path)

    summary = nlp.commit_job(1)
    assert summary["image_links"][0]["image_id"] == 77
    assert cur.sql_containing("INSERT INTO images")[0][1][0] == "activity"


def test_image_link_resolves_a_location(scripted, monkeypatch, tmp_path):
    data, _ = _image_job(tmp_path,
                         [{"entity_type": "location", "entity_name": "Nairobi",
                           "filename": "photo.jpg"}],
                         extra={"locations": [{"name": "Nairobi"}]})
    cur = scripted([_job(data), {"id": 11}, {"id": 77}])
    monkeypatch.setattr(nlp, "NLP_DIR", tmp_path)

    summary = nlp.commit_job(1)
    assert summary["image_links"][0]["image_id"] == 77
    assert cur.sql_containing("INSERT INTO images")[0][1][0] == "location"


# ── Selections interact with the commit ──────────────────────────────────
def test_selections_restrict_what_gets_written(scripted):
    data = dict(EMPTY, persons=[{"name": "Keep"}, {"name": "Drop"}])
    cur = scripted([_job(data), {"id": 1}])

    summary = nlp.commit_job(1, selections={"persons": [0]})
    assert summary["persons"] == [{"name": "Keep", "id": 1}]
    assert len(cur.sql_containing("INSERT INTO poi")) == 1
