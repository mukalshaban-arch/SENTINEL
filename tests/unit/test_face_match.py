"""Unit tests for face_match.py's pure functions: data-URI decoding,
embedding (de)serialization, cosine similarity, and the similarity->percent
display transform. The InsightFace model itself is lazy-loaded inside
_get_app(), so importing this module never downloads or loads it — the
detection/search paths that need it are covered in the integration suite."""
import base64

import numpy as np
import pytest

import face_match as fm


# ── data_uri_to_bytes ─────────────────────────────────────────────────────
def test_data_uri_to_bytes_decodes_prefixed_data_uri():
    payload = b"\x89PNG\r\n"
    uri = "data:image/png;base64," + base64.b64encode(payload).decode()
    assert fm.data_uri_to_bytes(uri) == payload


def test_data_uri_to_bytes_accepts_bare_base64():
    payload = b"rawbytes"
    assert fm.data_uri_to_bytes(base64.b64encode(payload).decode()) == payload


@pytest.mark.parametrize("value", ["", None])
def test_data_uri_to_bytes_returns_none_for_empty(value):
    assert fm.data_uri_to_bytes(value) is None


def test_data_uri_to_bytes_returns_none_on_bad_base64():
    assert fm.data_uri_to_bytes("data:image/png;base64,!!!not-base64!!!") is None


# ── embedding serialization round-trip ───────────────────────────────────
def test_embedding_bytes_roundtrip_preserves_values():
    emb = np.array([0.1, -0.5, 0.9], dtype=np.float32)
    restored = fm._bytes_to_embedding(fm._embedding_to_bytes(emb))
    np.testing.assert_allclose(restored, emb, rtol=1e-6)


def test_embedding_to_bytes_uses_float32():
    emb = np.array([1.0, 2.0], dtype=np.float64)
    raw = fm._embedding_to_bytes(emb)
    assert len(raw) == 2 * 4  # 2 values x 4 bytes (float32), not 8


def test_bytes_to_embedding_length_matches_input():
    emb = np.arange(512, dtype=np.float32)
    assert fm._bytes_to_embedding(fm._embedding_to_bytes(emb)).shape == (512,)


# ── cosine_similarity ─────────────────────────────────────────────────────
def test_cosine_similarity_identical_unit_vectors_is_one():
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert fm.cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_is_zero():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert fm.cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_opposite_is_negative_one():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([-1.0, 0.0], dtype=np.float32)
    assert fm.cosine_similarity(a, b) == pytest.approx(-1.0)


def test_cosine_similarity_returns_python_float():
    v = np.array([1.0, 0.0], dtype=np.float32)
    assert isinstance(fm.cosine_similarity(v, v), float)


# ── similarity_to_percent ────────────────────────────────────────────────
def test_similarity_to_percent_perfect_match_is_100():
    assert fm.similarity_to_percent(1.0) == 100.0


def test_similarity_to_percent_zero_is_zero():
    assert fm.similarity_to_percent(0.0) == 0.0


def test_similarity_to_percent_clamps_above_one():
    assert fm.similarity_to_percent(1.5) == 100.0


def test_similarity_to_percent_clamps_negative_to_zero():
    assert fm.similarity_to_percent(-0.4) == 0.0


def test_similarity_to_percent_applies_sqrt_lift():
    # 0.25 similarity -> sqrt(0.25) = 0.5 -> 50.0%, not 25%.
    assert fm.similarity_to_percent(0.25) == 50.0


def test_similarity_to_percent_is_monotonic():
    values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    percents = [fm.similarity_to_percent(v) for v in values]
    assert percents == sorted(percents)


def test_similarity_to_percent_rounds_to_one_decimal():
    result = fm.similarity_to_percent(0.3)
    assert result == round(result, 1)
