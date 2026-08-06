"""Unit tests for face_match.py's model- and database-backed paths:
face extraction, embedding storage, and the similarity search/ranking.

InsightFace and the DB are both stubbed. What's asserted is the logic
around them — best-embedding-per-POI selection, ranking order, the
likely-match threshold, and the never-raise guarantees that keep a corrupt
photo from blocking a save. The pure math lives in test_face_match.py.
"""
import numpy as np
import pytest

import face_match as fm


def _vec(*leading):
    """A 512-d float32 vector with the given leading values, zero-padded."""
    v = list(leading) + [0.0] * (fm.EMBEDDING_DIM - len(leading))
    return np.asarray(v, dtype=np.float32)


def _emb_bytes(vec):
    return np.asarray(vec, dtype=np.float32).tobytes()


class FakeFace:
    def __init__(self, vec, det_score=0.99, bbox=(1, 2, 3, 4)):
        self.normed_embedding = np.asarray(vec, dtype=np.float32)
        self.det_score = det_score
        self.bbox = np.asarray(bbox, dtype=np.float32)


class FakeApp:
    def __init__(self, faces=None, raises=False):
        self._faces = faces or []
        self._raises = raises

    def get(self, img):
        if self._raises:
            raise RuntimeError("detector exploded")
        return self._faces


# ── extract_faces ─────────────────────────────────────────────────────────
def test_extract_faces_returns_empty_without_model(monkeypatch):
    monkeypatch.setattr(fm, "_get_app", lambda: None)
    assert fm.extract_faces(b"imagebytes") == []


def test_extract_faces_returns_empty_for_empty_bytes(monkeypatch):
    monkeypatch.setattr(fm, "_get_app", lambda: FakeApp())
    assert fm.extract_faces(b"") == []


def test_extract_faces_returns_empty_when_image_undecodable(monkeypatch):
    monkeypatch.setattr(fm, "_get_app", lambda: FakeApp())
    monkeypatch.setattr(fm, "_decode_image_bytes", lambda raw: None)
    assert fm.extract_faces(b"not-an-image") == []


def test_extract_faces_maps_detector_output(monkeypatch):
    monkeypatch.setattr(fm, "_get_app", lambda: FakeApp([FakeFace(_vec(1.0), 0.87, (10, 20, 30, 40))]))
    monkeypatch.setattr(fm, "_decode_image_bytes", lambda raw: "fake-img")

    faces = fm.extract_faces(b"imagebytes")
    assert len(faces) == 1
    assert faces[0]["det_score"] == pytest.approx(0.87)
    assert faces[0]["bbox"] == [10.0, 20.0, 30.0, 40.0]
    assert faces[0]["embedding"].dtype == np.float32


def test_extract_faces_handles_multiple_faces(monkeypatch):
    monkeypatch.setattr(fm, "_get_app",
                        lambda: FakeApp([FakeFace(_vec(1.0)), FakeFace(_vec(0.0, 1.0))]))
    monkeypatch.setattr(fm, "_decode_image_bytes", lambda raw: "fake-img")
    assert len(fm.extract_faces(b"imagebytes")) == 2


def test_extract_faces_never_raises(monkeypatch):
    monkeypatch.setattr(fm, "_get_app", lambda: FakeApp(raises=True))
    monkeypatch.setattr(fm, "_decode_image_bytes", lambda raw: "fake-img")
    assert fm.extract_faces(b"imagebytes") == []


def test_engine_ready_reflects_model_availability(monkeypatch):
    monkeypatch.setattr(fm, "_get_app", lambda: None)
    assert fm.engine_ready() is False
    monkeypatch.setattr(fm, "_get_app", lambda: FakeApp())
    assert fm.engine_ready() is True


def test_get_app_returns_none_after_failed_load(monkeypatch):
    monkeypatch.setattr(fm, "_app", None)
    monkeypatch.setattr(fm, "_load_failed", True)
    assert fm._get_app() is None


def test_get_app_returns_cached_instance(monkeypatch):
    app = FakeApp()
    monkeypatch.setattr(fm, "_app", app)
    assert fm._get_app() is app


# ── store_embeddings_for_photo ───────────────────────────────────────────
def test_store_embeddings_clears_then_inserts(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [
        {"embedding": _vec(1.0), "det_score": 0.9, "bbox": [1, 2, 3, 4]},
    ])
    assert fm.store_embeddings_for_photo(7, "gallery", 3, b"img") == 1
    sqls = [c[0][0] for c in fake_db_cursor.execute.call_args_list]
    assert any("DELETE FROM face_embeddings" in s for s in sqls)
    assert any("INSERT INTO face_embeddings" in s for s in sqls)


def test_store_embeddings_stores_every_detected_face(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [
        {"embedding": _vec(1.0), "det_score": 0.9, "bbox": [1, 2, 3, 4]},
        {"embedding": _vec(0.0, 1.0), "det_score": 0.8, "bbox": [5, 6, 7, 8]},
    ])
    assert fm.store_embeddings_for_photo(7, "images", 3, b"img") == 2


def test_store_embeddings_with_no_faces_still_clears(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [])
    assert fm.store_embeddings_for_photo(7, "profile_photo", None, b"img") == 0
    sqls = [c[0][0] for c in fake_db_cursor.execute.call_args_list]
    assert any("DELETE FROM face_embeddings" in s for s in sqls)


def test_store_embeddings_returns_zero_on_db_error(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [])
    fake_db_cursor.execute.side_effect = Exception("db down")
    # Must swallow: a bad photo can never block the surrounding record save.
    assert fm.store_embeddings_for_photo(7, "gallery", 1, b"img") == 0


# ── search_similar_faces ─────────────────────────────────────────────────
def test_search_returns_nothing_when_no_face_detected(monkeypatch):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [])
    assert fm.search_similar_faces(b"img") == {"faces_detected": 0, "matches": []}


def test_search_returns_nothing_when_no_embeddings_stored(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [{"embedding": _vec(1.0)}])
    fake_db_cursor.fetchall.return_value = []
    assert fm.search_similar_faces(b"img") == {"faces_detected": 1, "matches": []}


def test_search_ranks_by_similarity_and_flags_likely_match(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [{"embedding": _vec(1.0)}])
    fake_db_cursor.fetchall.side_effect = [
        [
            {"id": 1, "poi_id": 11, "source": "gallery", "source_id": 1,
             "embedding": _emb_bytes(_vec(1.0)), "det_score": 0.9},        # sim 1.0
            {"id": 2, "poi_id": 22, "source": "images", "source_id": 2,
             "embedding": _emb_bytes(_vec(0.0, 1.0)), "det_score": 0.9},   # sim 0.0
        ],
        [
            {"id": 11, "alias": "Exact", "photo": None, "risk_level": "HIGH", "status": "ACTIVE"},
            {"id": 22, "alias": "Other", "photo": None, "risk_level": "LOW", "status": "ACTIVE"},
        ],
    ]

    result = fm.search_similar_faces(b"img")
    assert result["faces_detected"] == 1
    assert [m["alias"] for m in result["matches"]] == ["Exact", "Other"]
    assert result["matches"][0]["likely_match"] is True
    assert result["matches"][0]["percent"] == 100.0
    assert result["matches"][0]["matched_source"] == "gallery"
    assert result["matches"][1]["likely_match"] is False


def test_search_keeps_only_best_embedding_per_poi(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [{"embedding": _vec(1.0)}])
    fake_db_cursor.fetchall.side_effect = [
        [
            {"id": 1, "poi_id": 11, "source": "gallery", "source_id": 1,
             "embedding": _emb_bytes(_vec(0.0, 1.0)), "det_score": 0.9},
            {"id": 2, "poi_id": 11, "source": "images", "source_id": 2,
             "embedding": _emb_bytes(_vec(1.0)), "det_score": 0.9},
        ],
        [{"id": 11, "alias": "Only", "photo": None, "risk_level": "HIGH", "status": "ACTIVE"}],
    ]

    result = fm.search_similar_faces(b"img")
    assert len(result["matches"]) == 1
    assert result["matches"][0]["similarity"] == pytest.approx(1.0)
    assert result["matches"][0]["matched_source"] == "images"


def test_search_uses_best_across_multiple_query_faces(monkeypatch, fake_db_cursor):
    # Two faces in the uploaded image; the second one is the real match.
    monkeypatch.setattr(fm, "extract_faces",
                        lambda b: [{"embedding": _vec(0.0, 1.0)}, {"embedding": _vec(1.0)}])
    fake_db_cursor.fetchall.side_effect = [
        [{"id": 1, "poi_id": 11, "source": "gallery", "source_id": 1,
          "embedding": _emb_bytes(_vec(1.0)), "det_score": 0.9}],
        [{"id": 11, "alias": "Match", "photo": None, "risk_level": "HIGH", "status": "ACTIVE"}],
    ]
    result = fm.search_similar_faces(b"img")
    assert result["faces_detected"] == 2
    assert result["matches"][0]["similarity"] == pytest.approx(1.0)


def test_search_respects_top_n(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [{"embedding": _vec(1.0)}])
    fake_db_cursor.fetchall.side_effect = [
        [{"id": i, "poi_id": i, "source": "gallery", "source_id": i,
          "embedding": _emb_bytes(_vec(1.0)), "det_score": 0.9} for i in range(1, 6)],
        [{"id": i, "alias": f"P{i}", "photo": None, "risk_level": "LOW", "status": "ACTIVE"}
         for i in range(1, 6)],
    ]
    assert len(fm.search_similar_faces(b"img", top_n=2)["matches"]) == 2


def test_search_skips_pois_deleted_since_embedding_was_stored(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [{"embedding": _vec(1.0)}])
    fake_db_cursor.fetchall.side_effect = [
        [{"id": 1, "poi_id": 99, "source": "gallery", "source_id": 1,
          "embedding": _emb_bytes(_vec(1.0)), "det_score": 0.9}],
        [],  # the POI row no longer exists
    ]
    assert fm.search_similar_faces(b"img")["matches"] == []


def test_search_similarity_is_rounded_for_display(monkeypatch, fake_db_cursor):
    monkeypatch.setattr(fm, "extract_faces", lambda b: [{"embedding": _vec(1.0)}])
    fake_db_cursor.fetchall.side_effect = [
        [{"id": 1, "poi_id": 11, "source": "gallery", "source_id": 1,
          "embedding": _emb_bytes(_vec(0.123456789)), "det_score": 0.9}],
        [{"id": 11, "alias": "P", "photo": None, "risk_level": "LOW", "status": "ACTIVE"}],
    ]
    sim = fm.search_similar_faces(b"img")["matches"][0]["similarity"]
    assert sim == round(sim, 4)
