"""
SENTINEL – face_match.py
Fully offline face recognition: InsightFace (buffalo_l model pack) +
onnxruntime (CPU). Extracts a 512-d face embedding per detected face and
answers "who does this photo most resemble in our records?" via cosine
similarity against every embedding already on file for Persons of Interest.

Honest limitation: this is a similarity RANKING tool, not a forensic
identification system. The displayed "resemblance %" is a heuristic display
transform of cosine similarity, not a calibrated probability — appearance
changes (aging, facial hair, disguise, image quality) can lower true-match
scores, and superficially similar strangers can score higher than expected.
Treat results as investigative leads to verify, never as proof on their own.

Embeddings are stored once per photo (see store_embeddings_for_photo) so
matching against the whole corpus is fast — no re-running detection on every
search, just a similarity scan over already-extracted vectors.
"""

import io
import json
import base64
import logging

import numpy as np

from db import db_cursor

logger = logging.getLogger("sentinel.face")

MODEL_NAME = "buffalo_l"
EMBEDDING_DIM = 512
# ArcFace/buffalo_l cosine similarity for genuinely the same person is
# typically ~0.4+; unrelated faces usually cluster well below that. Used only
# to flag likely-same-person matches in results, not to filter them out.
LIKELY_MATCH_THRESHOLD = 0.40

_app = None
_load_failed = False


def _get_app():
    """Lazy-load the InsightFace pipeline so server startup never blocks on it."""
    global _app, _load_failed
    if _app is not None or _load_failed:
        return _app
    try:
        from insightface.app import FaceAnalysis
        _app = FaceAnalysis(name=MODEL_NAME, providers=["CPUExecutionProvider"])
        _app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace '%s' model loaded.", MODEL_NAME)
    except Exception as e:
        logger.error(
            "Could not load InsightFace model '%s' (%s). Face matching disabled "
            "until the model is available (downloads automatically on first use "
            "while online — see DEPLOYMENT.md).",
            MODEL_NAME, e,
        )
        _load_failed = True
    return _app


def engine_ready() -> bool:
    return _get_app() is not None


def _decode_image_bytes(raw: bytes):
    """bytes -> BGR numpy array (OpenCV convention), or None if undecodable."""
    import cv2
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def data_uri_to_bytes(data_uri: str) -> bytes | None:
    """Decode a `data:image/...;base64,....` string to raw image bytes."""
    if not data_uri:
        return None
    try:
        _, b64 = data_uri.split(",", 1) if "," in data_uri else (None, data_uri)
        return base64.b64decode(b64)
    except Exception as e:
        logger.warning("Could not decode data URI: %s", e)
        return None


def extract_faces(image_bytes: bytes) -> list[dict]:
    """
    Detect every face in an image and return its embedding + metadata.
    Returns [] if the model isn't available, the image can't be decoded, or
    no face is found. Never raises.

    Each item: {"embedding": np.float32[512] (L2-normalised), "det_score": float,
                "bbox": [x1,y1,x2,y2]}
    """
    app = _get_app()
    if app is None or not image_bytes:
        return []
    try:
        img = _decode_image_bytes(image_bytes)
        if img is None:
            return []
        faces = app.get(img)
        return [{
            "embedding": np.asarray(f.normed_embedding, dtype=np.float32),
            "det_score": float(f.det_score),
            "bbox": [float(x) for x in f.bbox],
        } for f in faces]
    except Exception as e:
        logger.warning("Face extraction failed: %s", e)
        return []


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """normed_embedding vectors are already unit-length, so the dot product
    IS the cosine similarity — no need to divide by norms again."""
    return float(np.dot(a, b))


def similarity_to_percent(sim: float) -> float:
    """Rescale cosine similarity to an analyst-facing 0-100 display number.

    Not a calibrated probability. Uses sqrt to lift the visually-relevant
    ~0.3-0.8 similarity band into a wider, more legible percentage spread —
    plain linear scaling makes a real same-person match (~0.4-0.5 similarity)
    look deceptively low (~40-50%).
    """
    clamped = max(0.0, min(1.0, sim))
    return round((clamped ** 0.5) * 100, 1)


def _embedding_to_bytes(emb: np.ndarray) -> bytes:
    return np.asarray(emb, dtype=np.float32).tobytes()


def _bytes_to_embedding(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw, dtype=np.float32)


def store_embeddings_for_photo(poi_id: int, source: str, source_id: int | None,
                                image_bytes: bytes) -> int:
    """
    Detect faces in `image_bytes` and (re-)store their embeddings for this
    POI's photo. Idempotent: clears any embeddings previously stored for the
    exact same (poi_id, source, source_id) before inserting fresh ones, so
    re-processing a photo (or overwriting one) never accumulates duplicates.

    source: one of 'profile_photo' | 'likeness' | 'gallery' | 'images'
    source_id: poi_gallery.id or images.id; None for profile_photo/likeness.
    Returns the number of faces stored. Never raises — logs and returns 0 on
    any failure, so a bad/corrupt photo never blocks the calling save.
    """
    try:
        faces = extract_faces(image_bytes)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "DELETE FROM face_embeddings WHERE poi_id=%s AND source=%s AND source_id IS NOT DISTINCT FROM %s",
                (poi_id, source, source_id),
            )
            for f in faces:
                cur.execute("""
                    INSERT INTO face_embeddings (poi_id, source, source_id, embedding, det_score, bbox)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (poi_id, source, source_id, _embedding_to_bytes(f["embedding"]),
                      f["det_score"], json.dumps(list(f["bbox"]))))
        return len(faces)
    except Exception:
        logger.exception("store_embeddings_for_photo failed (poi_id=%s, source=%s)", poi_id, source)
        return 0


def search_similar_faces(image_bytes: bytes, top_n: int = 10) -> dict:
    """
    Detect face(s) in a query image and rank every POI in the system by best
    cosine similarity across all of that POI's stored face embeddings.

    Returns {"faces_detected": N, "matches": [{"poi_id","alias","photo",
    "similarity","percent","likely_match","matched_source"}]} sorted by
    similarity descending, one row per POI (its single best-matching photo).
    Empty matches list if no face was found or no embeddings exist yet.
    """
    faces = extract_faces(image_bytes)
    if not faces:
        return {"faces_detected": 0, "matches": []}

    # If multiple faces are in the query image, match against each and keep
    # the best result per candidate face — the analyst reviews per-face.
    with db_cursor() as cur:
        cur.execute("SELECT id, poi_id, source, source_id, embedding, det_score FROM face_embeddings")
        rows = cur.fetchall()

    if not rows:
        return {"faces_detected": len(faces), "matches": []}

    stored = [{
        "poi_id": r["poi_id"], "source": r["source"], "source_id": r["source_id"],
        "embedding": _bytes_to_embedding(r["embedding"]),
    } for r in rows]

    # Best similarity per poi_id, across all query faces and all stored embeddings.
    best_per_poi: dict[int, dict] = {}
    for qf in faces:
        q_emb = qf["embedding"]
        for s in stored:
            sim = cosine_similarity(q_emb, s["embedding"])
            cur_best = best_per_poi.get(s["poi_id"])
            if cur_best is None or sim > cur_best["similarity"]:
                best_per_poi[s["poi_id"]] = {
                    "poi_id": s["poi_id"], "similarity": sim,
                    "source": s["source"], "source_id": s["source_id"],
                }

    ranked = sorted(best_per_poi.values(), key=lambda m: m["similarity"], reverse=True)[:top_n]
    if not ranked:
        return {"faces_detected": len(faces), "matches": []}

    poi_ids = [m["poi_id"] for m in ranked]
    with db_cursor() as cur:
        cur.execute("SELECT id, alias, photo, risk_level, status FROM poi WHERE id = ANY(%s)", (poi_ids,))
        poi_by_id = {r["id"]: r for r in cur.fetchall()}

    matches = []
    for m in ranked:
        poi = poi_by_id.get(m["poi_id"])
        if not poi:
            continue
        matches.append({
            "poi_id": poi["id"],
            "alias": poi["alias"],
            "photo": poi["photo"],
            "risk_level": poi["risk_level"],
            "status": poi["status"],
            "similarity": round(m["similarity"], 4),
            "percent": similarity_to_percent(m["similarity"]),
            "likely_match": m["similarity"] >= LIKELY_MATCH_THRESHOLD,
            "matched_source": m["source"],
        })
    return {"faces_detected": len(faces), "matches": matches}
