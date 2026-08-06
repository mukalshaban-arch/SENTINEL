"""Unit tests for nlp.py's job-pipeline logic: file-type dispatch, enum
normalisation, analyst selection filtering, hotspot proximity de-duplication,
and the process/commit job flows.

Extraction and OCR are stubbed — this covers the orchestration around them,
including the failure paths that decide whether a job ends up 'reviewed' or
'failed'.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import nlp


# ── extract_text_from_file: MIME dispatch ────────────────────────────────
def test_extract_text_reads_plain_text(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")
    assert nlp.extract_text_from_file(f, "text/plain") == "hello world"


def test_extract_text_reads_csv(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("col1,col2\n1,2", encoding="utf-8")
    assert "col1,col2" in nlp.extract_text_from_file(f, "text/csv")


def test_extract_text_mime_is_case_insensitive(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    assert nlp.extract_text_from_file(f, "TEXT/PLAIN") == "hello"


def test_extract_text_replaces_undecodable_bytes(tmp_path):
    f = tmp_path / "a.txt"
    f.write_bytes(b"valid \xff\xfe bytes")
    result = nlp.extract_text_from_file(f, "text/plain")
    assert "valid" in result  # errors="replace", never raises


def test_extract_text_unsupported_type(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"\x00\x01")
    assert nlp.extract_text_from_file(f, "application/octet-stream") == "[Unsupported file type]"


def test_extract_text_image_delegates_to_ocr(tmp_path, monkeypatch):
    monkeypatch.setattr(nlp, "ocr_image", lambda p: "text from image")
    f = tmp_path / "a.png"
    f.write_bytes(b"fake")
    assert nlp.extract_text_from_file(f, "image/png") == "text from image"


def test_extract_text_pdf_uses_pdfminer_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr(nlp, "PDF_AVAILABLE", True)
    monkeypatch.setattr(nlp, "pdf_extract_text", lambda p: "pdf text layer", raising=False)
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-")
    assert nlp.extract_text_from_file(f, "application/pdf") == "pdf text layer"


def test_extract_text_pdf_falls_back_to_ocr_when_no_text_layer(tmp_path, monkeypatch):
    monkeypatch.setattr(nlp, "PDF_AVAILABLE", True)
    monkeypatch.setattr(nlp, "pdf_extract_text", lambda p: "   ", raising=False)
    monkeypatch.setattr(nlp, "ocr_pdf_pages", lambda p: "ocr of scanned pdf")
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-")
    assert nlp.extract_text_from_file(f, "application/pdf") == "ocr of scanned pdf"


def test_extract_text_pdf_falls_back_to_ocr_when_pdfminer_raises(tmp_path, monkeypatch):
    def boom(p):
        raise RuntimeError("corrupt pdf")

    monkeypatch.setattr(nlp, "PDF_AVAILABLE", True)
    monkeypatch.setattr(nlp, "pdf_extract_text", boom, raising=False)
    monkeypatch.setattr(nlp, "ocr_pdf_pages", lambda p: "ocr rescue")
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-")
    assert nlp.extract_text_from_file(f, "application/pdf") == "ocr rescue"


def test_extract_text_pdf_uses_ocr_when_pdfminer_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(nlp, "PDF_AVAILABLE", False)
    monkeypatch.setattr(nlp, "ocr_pdf_pages", lambda p: "ocr only")
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-")
    assert nlp.extract_text_from_file(f, "application/pdf") == "ocr only"


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_extract_text_docx_reports_missing_library(tmp_path, monkeypatch):
    monkeypatch.setattr(nlp, "DOCX_AVAILABLE", False)
    f = tmp_path / "a.docx"
    f.write_bytes(b"PK")
    assert "python-docx" in nlp.extract_text_from_file(f, DOCX_MIME)


def test_extract_text_docx_joins_non_empty_paragraphs(tmp_path, monkeypatch):
    class P:
        def __init__(self, text):
            self.text = text

    class Doc:
        paragraphs = [P("first"), P("   "), P("second")]

    monkeypatch.setattr(nlp, "DOCX_AVAILABLE", True)
    monkeypatch.setattr(nlp, "DocxDocument", lambda p: Doc(), raising=False)
    f = tmp_path / "a.docx"
    f.write_bytes(b"PK")
    assert nlp.extract_text_from_file(f, DOCX_MIME) == "first\nsecond"


def test_extract_text_docx_reports_failure(tmp_path, monkeypatch):
    def boom(p):
        raise RuntimeError("bad docx")

    monkeypatch.setattr(nlp, "DOCX_AVAILABLE", True)
    monkeypatch.setattr(nlp, "DocxDocument", boom, raising=False)
    f = tmp_path / "a.docx"
    f.write_bytes(b"PK")
    assert "DOCX extraction failed" in nlp.extract_text_from_file(f, DOCX_MIME)


# ── Enum normalisation ────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("MEETING", "MEETING"),
    ("meeting", "MEETING"),
    ("  Meeting  ", "MEETING"),
    ("NOT_A_TYPE", "OTHER"),
    ("", "OTHER"),
    (None, "OTHER"),
    (12345, "OTHER"),
])
def test_map_activity_type(raw, expected):
    assert nlp._map_activity_type(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("GENERAL", "GENERAL"),
    ("not a type", "GENERAL"),
    ("", "GENERAL"),
    (None, "GENERAL"),
])
def test_map_hotspot_type_falls_back_to_general(raw, expected):
    assert nlp._map_hotspot_type(raw) == expected


def test_map_hotspot_type_normalises_spaces_to_underscores():
    # Whatever the valid set is, spaces must become underscores before lookup.
    for valid in nlp._HOTSPOT_TYPES:
        if "_" in valid:
            spaced = valid.replace("_", " ").lower()
            assert nlp._map_hotspot_type(spaced) == valid
            break


# ── _apply_selections ─────────────────────────────────────────────────────
DATA = {
    "persons":    [{"name": "A"}, {"name": "B"}, {"name": "C"}],
    "groups":     [{"name": "G1"}, {"name": "G2"}],
    "locations":  [{"name": "L1"}],
    "activities": [{"title": "Act1"}, {"title": "Act2"}],
    "image_links": [
        {"entity_name": "A", "filename": "a.jpg"},
        {"entity_name": "C", "filename": "c.jpg"},
        {"entity_name": "G2", "filename": "g2.jpg"},
    ],
}


def test_apply_selections_none_returns_everything():
    assert nlp._apply_selections(DATA, None) is DATA


def test_apply_selections_empty_dict_returns_everything():
    assert nlp._apply_selections(DATA, {}) is DATA


def test_apply_selections_filters_by_index():
    result = nlp._apply_selections(DATA, {"persons": [0, 2]})
    assert [p["name"] for p in result["persons"]] == ["A", "C"]


def test_apply_selections_omitted_key_keeps_all_of_that_type():
    result = nlp._apply_selections(DATA, {"persons": [0]})
    assert len(result["groups"]) == 2  # groups not mentioned -> unfiltered


def test_apply_selections_empty_list_selects_none():
    result = nlp._apply_selections(DATA, {"persons": []})
    assert result["persons"] == []


def test_apply_selections_ignores_out_of_range_indices():
    result = nlp._apply_selections(DATA, {"persons": [0, 99, -5]})
    assert [p["name"] for p in result["persons"]] == ["A"]


def test_apply_selections_drops_image_links_to_deselected_entities():
    result = nlp._apply_selections(DATA, {"persons": [0], "groups": [0], "locations": []})
    names = {im["entity_name"] for im in result["image_links"]}
    assert names == {"A"}          # C deselected, G2 deselected


def test_apply_selections_does_not_mutate_input():
    original = {k: (list(v) if isinstance(v, list) else v) for k, v in DATA.items()}
    nlp._apply_selections(DATA, {"persons": [0]})
    assert DATA == original


def test_apply_selections_handles_missing_keys():
    result = nlp._apply_selections({}, {"persons": [0]})
    assert result["persons"] == []
    assert result["image_links"] == []


# ── _find_nearby_hotspot (geopandas dedup) ───────────────────────────────
def test_find_nearby_hotspot_returns_none_without_geopandas(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("geopandas", "shapely.geometry"):
            raise ImportError("not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert nlp._find_nearby_hotspot(0.0, 0.0) is None


def test_find_nearby_hotspot_returns_none_when_no_hotspots(monkeypatch, fake_db_cursor):
    pytest.importorskip("geopandas")
    monkeypatch.setattr(nlp, "db_cursor", _cm(fake_db_cursor))
    fake_db_cursor.fetchall.return_value = []
    assert nlp._find_nearby_hotspot(0.0, 0.0) is None


def test_find_nearby_hotspot_finds_a_close_point(monkeypatch, fake_db_cursor):
    pytest.importorskip("geopandas")
    monkeypatch.setattr(nlp, "db_cursor", _cm(fake_db_cursor))
    # ~30m away from the target at this latitude.
    fake_db_cursor.fetchall.return_value = [{"id": 7, "lat": -1.2900, "lng": 36.8200}]
    assert nlp._find_nearby_hotspot(-1.29005, 36.82005) == 7


def test_find_nearby_hotspot_ignores_a_distant_point(monkeypatch, fake_db_cursor):
    pytest.importorskip("geopandas")
    monkeypatch.setattr(nlp, "db_cursor", _cm(fake_db_cursor))
    fake_db_cursor.fetchall.return_value = [{"id": 7, "lat": 10.0, "lng": 40.0}]
    assert nlp._find_nearby_hotspot(-1.29, 36.82) is None


def test_find_nearby_hotspot_swallows_errors(monkeypatch, fake_db_cursor):
    pytest.importorskip("geopandas")
    monkeypatch.setattr(nlp, "db_cursor", _cm(fake_db_cursor))
    fake_db_cursor.execute.side_effect = Exception("db down")
    assert nlp._find_nearby_hotspot(0.0, 0.0) is None


def _cm(cursor):
    """Wrap a mock cursor in a db_cursor-compatible context manager."""
    from contextlib import contextmanager

    @contextmanager
    def _fake(commit: bool = False):
        yield cursor

    return _fake


# ── process_job ───────────────────────────────────────────────────────────
def test_process_job_marks_job_reviewed(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(nlp, "db_cursor", _cm(fake_db_cursor))
    monkeypatch.setattr(nlp, "extract_entities", lambda text: {
        "persons": [], "groups": [], "locations": [], "activities": [], "image_links": []})
    monkeypatch.setattr(nlp, "match_images_to_entities", lambda imgs, ents: [])

    nlp.process_job(1, "some report text", [])
    sqls = " ".join(c[0][0] for c in fake_db_cursor.execute.call_args_list)
    assert "reviewed" in sqls


def test_process_job_marks_job_failed_on_error(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(nlp, "db_cursor", _cm(fake_db_cursor))

    def boom(text):
        raise RuntimeError("extraction blew up")

    monkeypatch.setattr(nlp, "extract_entities", boom)
    nlp.process_job(1, "text", [])
    sqls = " ".join(c[0][0] for c in fake_db_cursor.execute.call_args_list)
    assert "failed" in sqls


# ── commit_job ────────────────────────────────────────────────────────────
def test_commit_job_raises_for_unknown_job(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(nlp, "db_cursor", _cm(fake_db_cursor))
    fake_db_cursor.fetchone.return_value = None
    with pytest.raises(ValueError):
        nlp.commit_job(999)
