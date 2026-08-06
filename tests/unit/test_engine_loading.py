"""Tests for the lazy engine loaders in ocr_offline.py and face_match.py.

These are the `try: import <heavy ML lib>` bodies that normally only run on
a machine with the models installed. Stand-in modules are injected into
sys.modules so both the success and failure branches execute — that's what
guarantees a missing model degrades to a clear placeholder/None rather than
crashing document ingestion or the face-search endpoint.
"""
import sys
import types

import numpy as np
import pytest

import face_match as fm
import ocr_offline as ocr


@pytest.fixture(autouse=True)
def _reset_module_state(monkeypatch):
    monkeypatch.setattr(ocr, "_paddle_reader", None)
    monkeypatch.setattr(ocr, "_paddle_load_failed", False)
    monkeypatch.setattr(ocr, "_easyocr_reader", None)
    monkeypatch.setattr(ocr, "_easyocr_load_failed", False)
    monkeypatch.setattr(fm, "_app", None)
    monkeypatch.setattr(fm, "_load_failed", False)


# ── PaddleOCR loader ──────────────────────────────────────────────────────
def test_get_paddle_constructs_the_reader(monkeypatch):
    built = {}

    class FakePaddleOCR:
        def __init__(self, **kwargs):
            built.update(kwargs)

    fake = types.ModuleType("paddleocr")
    fake.PaddleOCR = FakePaddleOCR
    monkeypatch.setitem(sys.modules, "paddleocr", fake)

    reader = ocr._get_paddle()
    assert isinstance(reader, FakePaddleOCR)
    # enable_mkldnn=False works around a PaddlePaddle oneDNN crash — if this
    # ever flips to True, that regression should be caught here.
    assert built["enable_mkldnn"] is False
    assert built["lang"] == "en"


def test_get_paddle_marks_failure_when_import_raises(monkeypatch):
    def bad_import(name, *a, **kw):
        if name == "paddleocr":
            raise ImportError("paddleocr not installed")
        return real_import(name, *a, **kw)

    import builtins
    real_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", bad_import)

    assert ocr._get_paddle() is None
    assert ocr._paddle_load_failed is True


def test_get_paddle_marks_failure_when_construction_raises(monkeypatch):
    class Exploding:
        def __init__(self, **kwargs):
            raise RuntimeError("no model weights cached")

    fake = types.ModuleType("paddleocr")
    fake.PaddleOCR = Exploding
    monkeypatch.setitem(sys.modules, "paddleocr", fake)

    assert ocr._get_paddle() is None
    assert ocr._paddle_load_failed is True


# ── EasyOCR loader ────────────────────────────────────────────────────────
def test_get_easyocr_constructs_the_reader(monkeypatch):
    built = {}

    class FakeReader:
        def __init__(self, langs, gpu=False, verbose=True):
            built["langs"] = langs
            built["gpu"] = gpu

    fake = types.ModuleType("easyocr")
    fake.Reader = FakeReader
    monkeypatch.setitem(sys.modules, "easyocr", fake)

    reader = ocr._get_easyocr()
    assert isinstance(reader, FakeReader)
    assert built["langs"] == ["en"]
    assert built["gpu"] is False   # CPU-only by design


def test_get_easyocr_marks_failure_when_construction_raises(monkeypatch):
    class Exploding:
        def __init__(self, *a, **kw):
            raise RuntimeError("no weights")

    fake = types.ModuleType("easyocr")
    fake.Reader = Exploding
    monkeypatch.setitem(sys.modules, "easyocr", fake)

    assert ocr._get_easyocr() is None
    assert ocr._easyocr_load_failed is True


# ── InsightFace loader ────────────────────────────────────────────────────
def test_get_app_loads_and_prepares_the_model(monkeypatch):
    calls = {}

    class FakeFaceAnalysis:
        def __init__(self, name=None, providers=None):
            calls["name"] = name
            calls["providers"] = providers

        def prepare(self, ctx_id=0, det_size=None):
            calls["prepared"] = (ctx_id, det_size)

    app_mod = types.ModuleType("insightface.app")
    app_mod.FaceAnalysis = FakeFaceAnalysis
    pkg = types.ModuleType("insightface")
    pkg.app = app_mod
    monkeypatch.setitem(sys.modules, "insightface", pkg)
    monkeypatch.setitem(sys.modules, "insightface.app", app_mod)

    app = fm._get_app()
    assert isinstance(app, FakeFaceAnalysis)
    assert calls["name"] == fm.MODEL_NAME
    assert calls["providers"] == ["CPUExecutionProvider"]   # CPU-only by design
    assert calls["prepared"] == (0, (640, 640))


def test_get_app_marks_failure_when_model_missing(monkeypatch):
    class Exploding:
        def __init__(self, **kwargs):
            raise RuntimeError("buffalo_l not downloaded")

    app_mod = types.ModuleType("insightface.app")
    app_mod.FaceAnalysis = Exploding
    pkg = types.ModuleType("insightface")
    pkg.app = app_mod
    monkeypatch.setitem(sys.modules, "insightface", pkg)
    monkeypatch.setitem(sys.modules, "insightface.app", app_mod)

    assert fm._get_app() is None
    assert fm._load_failed is True


def test_get_app_marks_failure_when_import_raises(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def bad_import(name, *a, **kw):
        if name.startswith("insightface"):
            raise ImportError("insightface not installed")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", bad_import)
    assert fm._get_app() is None
    assert fm._load_failed is True


# ── Image decoding (OpenCV boundary) ─────────────────────────────────────
def test_decode_image_bytes_delegates_to_cv2(monkeypatch):
    decoded = np.zeros((2, 2, 3), dtype=np.uint8)
    fake_cv2 = types.ModuleType("cv2")
    fake_cv2.IMREAD_COLOR = 1
    fake_cv2.imdecode = lambda arr, flag: decoded
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    result = fm._decode_image_bytes(b"\xff\xd8\xff")
    assert result is decoded


def test_decode_image_bytes_returns_none_for_undecodable_input(monkeypatch):
    fake_cv2 = types.ModuleType("cv2")
    fake_cv2.IMREAD_COLOR = 1
    fake_cv2.imdecode = lambda arr, flag: None   # what cv2 returns on garbage
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    assert fm._decode_image_bytes(b"not-an-image") is None
