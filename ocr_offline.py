"""
SENTINEL – ocr_offline.py
Fully offline OCR: PaddleOCR primary, EasyOCR fallback.

Both engines download their model weights once (on first use, when online)
into a local cache (~/.paddlex and ~/.EasyOCR) and run entirely offline after
that — no API calls, ever. If neither engine's weights are cached yet, OCR
functions return a clear placeholder string instead of raising, so document
ingestion never crashes because the models aren't downloaded yet.

Engines are loaded lazily (only on first actual OCR call) so server startup
never blocks on loading multi-hundred-MB models.
"""

import logging
from pathlib import Path

logger = logging.getLogger("sentinel.ocr")

_paddle_reader = None
_paddle_load_failed = False
_easyocr_reader = None
_easyocr_load_failed = False


def _get_paddle():
    global _paddle_reader, _paddle_load_failed
    if _paddle_reader is not None or _paddle_load_failed:
        return _paddle_reader
    try:
        from paddleocr import PaddleOCR
        # enable_mkldnn=False works around a PaddlePaddle/oneDNN PIR-executor
        # crash (NotImplementedError in onednn_instruction.cc) seen on some
        # CPUs with paddlepaddle 3.x — costs some speed, not correctness.
        _paddle_reader = PaddleOCR(use_textline_orientation=True, lang="en", enable_mkldnn=False)
        logger.info("PaddleOCR engine loaded.")
    except Exception as e:
        logger.warning("PaddleOCR unavailable (%s) — will try EasyOCR.", e)
        _paddle_load_failed = True
    return _paddle_reader


def _get_easyocr():
    global _easyocr_reader, _easyocr_load_failed
    if _easyocr_reader is not None or _easyocr_load_failed:
        return _easyocr_reader
    try:
        import easyocr
        _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        logger.info("EasyOCR engine loaded.")
    except Exception as e:
        logger.warning("EasyOCR unavailable (%s).", e)
        _easyocr_load_failed = True
    return _easyocr_reader


def ocr_image(path: Path) -> str:
    """
    Run OCR on an image file. Tries PaddleOCR first, falls back to EasyOCR.
    Never raises — returns a bracketed placeholder if both engines are
    unavailable or both fail on this particular image.
    """
    path = str(path)

    paddle = _get_paddle()
    if paddle is not None:
        try:
            lines = []
            for res in paddle.predict(path):
                lines.extend(res.get("rec_texts", []) or [])
            text = "\n".join(t for t in lines if t.strip())
            if text.strip():
                return text
        except Exception as e:
            logger.warning("PaddleOCR failed on %s (%s) — trying EasyOCR.", path, e)

    reader = _get_easyocr()
    if reader is not None:
        try:
            lines = reader.readtext(path, detail=0)
            text = "\n".join(t for t in lines if t.strip())
            if text.strip():
                return text
        except Exception as e:
            logger.warning("EasyOCR failed on %s (%s).", path, e)

    if paddle is None and reader is None:
        return ("[OCR unavailable — model weights not downloaded yet. On a machine with "
                "internet access, run the server once (or `python -c \"from paddleocr import "
                "PaddleOCR; PaddleOCR(lang='en')\"`) to cache the models, then copy "
                "~/.paddlex and/or ~/.EasyOCR to this machine for fully offline use.]")
    return "[No text detected in image]"


def ocr_pdf_pages(path: Path) -> str:
    """OCR a PDF that has no extractable text layer, page by page."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return "[pdf2image not installed — cannot rasterize PDF pages for OCR]"
    try:
        pages = convert_from_path(str(path))
    except Exception as e:
        return f"[PDF rasterization failed: {e}]"

    tmp_dir = path.parent
    parts = []
    for i, page in enumerate(pages):
        tmp_path = tmp_dir / f"{path.stem}_ocr_page{i}.png"
        try:
            page.save(tmp_path)
            text = ocr_image(tmp_path)
            if text.strip() and not text.startswith("["):
                parts.append(f"--- Page {i + 1} ---\n{text}")
        finally:
            tmp_path.unlink(missing_ok=True)
    return "\n".join(parts) if parts else "[No text found via OCR in PDF pages]"


def engines_ready() -> dict:
    """Best-effort status check, for the /api/nlp/status-style diagnostics."""
    return {
        "paddleocr": _get_paddle() is not None,
        "easyocr": _get_easyocr() is not None,
    }
