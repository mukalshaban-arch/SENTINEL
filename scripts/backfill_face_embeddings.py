"""
SENTINEL – scripts/backfill_face_embeddings.py
One-time (or re-run anytime) pass over every existing POI photo — profile
photo, likeness, gallery, and the generic images table — extracting and
storing face embeddings for any that don't have one yet. Photos uploaded
through the app itself are embedded automatically on save; this script is
for photos that got into the database another way (a bulk import, a direct
SQL load, or photos added before this feature existed).

Usage (from the SENTINEL project root, with the venv active):
    python scripts/backfill_face_embeddings.py [--force]

--force re-processes photos that already have an embedding (useful after
upgrading the model). Without it, only photos with zero rows in
face_embeddings for their (poi_id, source, source_id) are processed.
"""

import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import os


def _load_dotenv():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

import db
import face_match


def _already_embedded(cur, poi_id, source, source_id) -> bool:
    cur.execute(
        "SELECT 1 FROM face_embeddings WHERE poi_id=%s AND source=%s AND source_id IS NOT DISTINCT FROM %s LIMIT 1",
        (poi_id, source, source_id),
    )
    return cur.fetchone() is not None


def main():
    ap = argparse.ArgumentParser(description="Backfill face embeddings for existing POI photos.")
    ap.add_argument("--force", action="store_true", help="Re-process photos that already have an embedding.")
    args = ap.parse_args()

    db.init_pool()
    if not face_match.engine_ready():
        sys.exit("Face recognition model is not available (InsightFace failed to load) — "
                 "see server logs / DEPLOYMENT.md for the model download step.")

    checked = processed = faces_found = 0

    with db.db_cursor() as cur:
        cur.execute("SELECT id, photo, likeness FROM poi")
        pois = cur.fetchall()

    for p in pois:
        for col, source in (("photo", "profile_photo"), ("likeness", "likeness")):
            data_uri = p[col]
            if not data_uri:
                continue
            checked += 1
            with db.db_cursor() as cur:
                skip = not args.force and _already_embedded(cur, p["id"], source, None)
            if skip:
                continue
            img_bytes = face_match.data_uri_to_bytes(data_uri)
            if not img_bytes:
                continue
            n = face_match.store_embeddings_for_photo(p["id"], source, None, img_bytes)
            processed += 1
            faces_found += n
            print(f"  poi #{p['id']} {source}: {n} face(s)")

    with db.db_cursor() as cur:
        cur.execute("SELECT id, poi_id, src FROM poi_gallery")
        gallery_rows = cur.fetchall()

    for g in gallery_rows:
        checked += 1
        with db.db_cursor() as cur:
            skip = not args.force and _already_embedded(cur, g["poi_id"], "gallery", g["id"])
        if skip:
            continue
        img_bytes = face_match.data_uri_to_bytes(g["src"])
        if not img_bytes:
            continue
        n = face_match.store_embeddings_for_photo(g["poi_id"], "gallery", g["id"], img_bytes)
        processed += 1
        faces_found += n
        print(f"  poi #{g['poi_id']} gallery #{g['id']}: {n} face(s)")

    with db.db_cursor() as cur:
        cur.execute("SELECT id, entity_id, content FROM images WHERE entity_type='person'")
        image_rows = cur.fetchall()

    for im in image_rows:
        checked += 1
        with db.db_cursor() as cur:
            skip = not args.force and _already_embedded(cur, im["entity_id"], "images", im["id"])
        if skip:
            continue
        img_bytes = face_match.data_uri_to_bytes(im["content"])
        if not img_bytes:
            continue
        n = face_match.store_embeddings_for_photo(im["entity_id"], "images", im["id"], img_bytes)
        processed += 1
        faces_found += n
        print(f"  poi #{im['entity_id']} image #{im['id']}: {n} face(s)")

    print(f"\nDone. Checked {checked} photo(s), processed {processed}, found {faces_found} face(s) total.")


if __name__ == "__main__":
    main()
