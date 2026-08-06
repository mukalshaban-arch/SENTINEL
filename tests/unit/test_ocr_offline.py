"""Unit tests for ocr_offline.py's engine-selection and fallback logic.

The actual OCR engines are stubbed — what matters here is the decision
tree: PaddleOCR first, EasyOCR on failure/empty, and a clearly-bracketed
placeholder (never an exception) when neither is usable. That contract is
what keeps document ingestion from crashing on a machine where the model
weights were never downloaded.
"""
from pathlib import Path

import pytest

import ocr_offline as ocr


@pytest.fixture(autouse=True)
def _reset_engine_state(monkeypatch):
    """Engines are cached in module globals; reset per test so one test's
    stub doesn't leak into the next."""
    monkeypatch.setattr(ocr, "_paddle_reader", None)
    monkeypatch.setattr(ocr, "_paddle_load_failed", False)
    monkeypatch.setattr(ocr, "_easyocr_reader", None)
    monkeypatch.setattr(ocr, "_easyocr_load_failed", False)


class FakePaddle:
    def __init__(self, texts=None, raises=False):
        self._texts = texts or []
        self._raises = raises

    def predict(self, path):
        if self._raises:
            raise RuntimeError("paddle exploded")
        return [{"rec_texts": self._texts}]


class FakeEasy:
    def __init__(self, texts=None, raises=False):
        self._texts = texts or []
        self._raises = raises

    def readtext(self, path, detail=0):
        if self._raises:
            raise RuntimeError("easyocr exploded")
        return self._texts


def _use(monkeypatch, paddle=None, easy=None):
    monkeypatch.setattr(ocr, "_get_paddle", lambda: paddle)
    monkeypatch.setattr(ocr, "_get_easyocr", lambda: easy)


# ── Happy paths ──────────────────────────────────────────────────────────
def test_paddle_result_is_used_when_available(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle(["hello", "world"]), easy=FakeEasy(["should not be used"]))
    assert ocr.ocr_image(Path("x.png")) == "hello\nworld"


def test_blank_paddle_lines_are_dropped(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle(["hello", "   ", "", "world"]))
    assert ocr.ocr_image(Path("x.png")) == "hello\nworld"


def test_easyocr_used_when_paddle_unavailable(monkeypatch):
    _use(monkeypatch, paddle=None, easy=FakeEasy(["from easyocr"]))
    assert ocr.ocr_image(Path("x.png")) == "from easyocr"


# ── Fallback behaviour ───────────────────────────────────────────────────
def test_falls_back_to_easyocr_when_paddle_raises(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle(raises=True), easy=FakeEasy(["rescued by easyocr"]))
    assert ocr.ocr_image(Path("x.png")) == "rescued by easyocr"


def test_falls_back_to_easyocr_when_paddle_finds_nothing(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle([]), easy=FakeEasy(["easyocr found text"]))
    assert ocr.ocr_image(Path("x.png")) == "easyocr found text"


def test_no_text_placeholder_when_both_engines_find_nothing(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle([]), easy=FakeEasy([]))
    assert ocr.ocr_image(Path("x.png")) == "[No text detected in image]"


def test_no_text_placeholder_when_both_engines_raise(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle(raises=True), easy=FakeEasy(raises=True))
    assert ocr.ocr_image(Path("x.png")) == "[No text detected in image]"


def test_unavailable_placeholder_when_no_engine_loads(monkeypatch):
    _use(monkeypatch, paddle=None, easy=None)
    result = ocr.ocr_image(Path("x.png"))
    assert result.startswith("[OCR unavailable")
    assert "paddlex" in result or ".paddlex" in result


def test_ocr_image_never_raises(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle(raises=True), easy=FakeEasy(raises=True))
    # Must return a string, not propagate — ingestion depends on this.
    assert isinstance(ocr.ocr_image(Path("x.png")), str)


def test_ocr_image_accepts_str_and_path(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle(["ok"]))
    assert ocr.ocr_image("x.png") == "ok"
    assert ocr.ocr_image(Path("x.png")) == "ok"


# ── Engine loader caching ────────────────────────────────────────────────
def test_get_paddle_returns_none_after_a_failed_load(monkeypatch):
    monkeypatch.setattr(ocr, "_paddle_load_failed", True)
    assert ocr._get_paddle() is None


def test_get_easyocr_returns_none_after_a_failed_load(monkeypatch):
    monkeypatch.setattr(ocr, "_easyocr_load_failed", True)
    assert ocr._get_easyocr() is None


def test_get_paddle_returns_cached_reader(monkeypatch):
    sentinel = FakePaddle(["cached"])
    monkeypatch.setattr(ocr, "_paddle_reader", sentinel)
    assert ocr._get_paddle() is sentinel


def test_get_easyocr_returns_cached_reader(monkeypatch):
    sentinel = FakeEasy(["cached"])
    monkeypatch.setattr(ocr, "_easyocr_reader", sentinel)
    assert ocr._get_easyocr() is sentinel


# ── engines_ready diagnostics ────────────────────────────────────────────
def test_engines_ready_reports_both_available(monkeypatch):
    _use(monkeypatch, paddle=FakePaddle(), easy=FakeEasy())
    assert ocr.engines_ready() == {"paddleocr": True, "easyocr": True}


def test_engines_ready_reports_neither_available(monkeypatch):
    _use(monkeypatch, paddle=None, easy=None)
    assert ocr.engines_ready() == {"paddleocr": False, "easyocr": False}


def test_engines_ready_reports_mixed(monkeypatch):
    _use(monkeypatch, paddle=None, easy=FakeEasy())
    assert ocr.engines_ready() == {"paddleocr": False, "easyocr": True}


# ── PDF page OCR ─────────────────────────────────────────────────────────
def test_ocr_pdf_pages_reports_missing_pdf2image(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pdf2image":
            raise ImportError("no pdf2image")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = ocr.ocr_pdf_pages(Path("doc.pdf"))
    assert "pdf2image not installed" in result


def test_ocr_pdf_pages_reports_rasterization_failure(monkeypatch, tmp_path):
    fake_module = type("M", (), {"convert_from_path": staticmethod(
        lambda p: (_ for _ in ()).throw(RuntimeError("poppler missing")))})
    monkeypatch.setitem(__import__("sys").modules, "pdf2image", fake_module)
    result = ocr.ocr_pdf_pages(tmp_path / "doc.pdf")
    assert "PDF rasterization failed" in result


def test_ocr_pdf_pages_joins_page_text(monkeypatch, tmp_path):
    class FakePage:
        def save(self, path):
            Path(path).write_bytes(b"fake")

    fake_module = type("M", (), {"convert_from_path": staticmethod(lambda p: [FakePage(), FakePage()])})
    monkeypatch.setitem(__import__("sys").modules, "pdf2image", fake_module)
    monkeypatch.setattr(ocr, "ocr_image", lambda p: "page text")

    result = ocr.ocr_pdf_pages(tmp_path / "doc.pdf")
    assert "--- Page 1 ---" in result and "--- Page 2 ---" in result


def test_ocr_pdf_pages_placeholder_when_no_text_found(monkeypatch, tmp_path):
    class FakePage:
        def save(self, path):
            Path(path).write_bytes(b"fake")

    fake_module = type("M", (), {"convert_from_path": staticmethod(lambda p: [FakePage()])})
    monkeypatch.setitem(__import__("sys").modules, "pdf2image", fake_module)
    monkeypatch.setattr(ocr, "ocr_image", lambda p: "[No text detected in image]")

    result = ocr.ocr_pdf_pages(tmp_path / "doc.pdf")
    assert result == "[No text found via OCR in PDF pages]"
