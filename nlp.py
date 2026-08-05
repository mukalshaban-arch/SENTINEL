"""
SENTINEL – nlp.py
Fully offline intelligence extraction module — no external API calls.

Supports:
  - Plain text input
  - PDF  (text extraction via pdfminer.six, fallback OCR via ocr_offline)
  - Word documents (.docx via python-docx)
  - Images (JPEG, PNG, TIFF, BMP, WEBP — OCR via ocr_offline: PaddleOCR + EasyOCR fallback)
  - CSV / TXT files

Entity extraction (nlp_extract.py: spaCy NER + rule-based enrichment) returns
structured JSON:
  {
    "persons":    [{ "name", "aliases", "nationality", "notes" }],
    "groups":     [{ "name", "category", "description", "notes" }],
    "locations":  [{ "name", "address", "country", "type", "notes" }],
    "activities": [{ "title", "type", "date", "notes", "poi_names", "group_names", "location_name" }],
    "image_links":[{ "entity_type", "entity_name", "filename", "reason", "confidence" }]
  }

Image association:
  Offline substitute for vision-based matching: each submitted image is OCR'd
  and its text is checked for extracted entity names (nlp_extract.match_images_to_entities).
  This only catches labelled/captioned imagery — anything it misses can still
  be attached manually from the entity's own photo panel.

Endpoints (all require analyst or admin role):
  POST /api/nlp/submit          — multipart upload: field "text" or files
  GET  /api/nlp/jobs            — list all jobs
  GET  /api/nlp/jobs/<id>       — get job + extracted entities
  POST /api/nlp/jobs/<id>/commit — accept and write entities to DB
  POST /api/nlp/jobs/<id>/reject — discard job
"""

import io
import json
import uuid
import base64
import logging
import traceback
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Optional dependency flags ────────────────────────────────────────────────
try:
    from pdfminer.high_level import extract_text as pdf_extract_text
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pdfminer.six not installed — PDF text extraction disabled.")

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not installed — .docx extraction disabled.")

from db import db_cursor
from geocode import geocode
from ocr_offline import ocr_image, ocr_pdf_pages
from nlp_extract import extract_entities, match_images_to_entities

UPLOADS_DIR = Path(__file__).parent / "uploads"
NLP_DIR     = UPLOADS_DIR / "nlp"
NLP_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/csv",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg", "image/jpg", "image/png", "image/tiff",
    "image/bmp", "image/webp",
}

IMAGE_MIME_TYPES = {"image/jpeg","image/jpg","image/png","image/tiff","image/bmp","image/webp"}

# ─────────────────────────────────────────────────────────────────────────────
# Text extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_text_from_file(filepath: Path, mime_type: str) -> str:
    """Extract plain text from any supported file type."""
    mime = mime_type.lower()

    if mime in ("text/plain", "text/csv"):
        return filepath.read_text(encoding="utf-8", errors="replace")

    if mime == "application/pdf":
        if PDF_AVAILABLE:
            try:
                text = pdf_extract_text(str(filepath))
                if text and text.strip():
                    return text
            except Exception as e:
                logger.warning("pdfminer failed: %s — trying OCR", e)
        # Fallback: OCR each page as image (scanned/image-only PDF)
        return ocr_pdf_pages(filepath)

    if mime in ("application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        if DOCX_AVAILABLE:
            try:
                doc = DocxDocument(str(filepath))
                return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            except Exception as e:
                return f"[DOCX extraction failed: {e}]"
        return "[DOCX extraction unavailable — install python-docx]"

    if mime in IMAGE_MIME_TYPES:
        return ocr_image(filepath)

    return "[Unsupported file type]"


# ─────────────────────────────────────────────────────────────────────────────
# Claude API helpers
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Job processing
# ─────────────────────────────────────────────────────────────────────────────

def process_job(job_id: int, text: str, image_files: list[dict]) -> None:
    """
    Run offline entity extraction + image linking for a job.
    Called in a background thread from the server.
    """
    try:
        # 1. Extract entities from text (spaCy NER + rule-based enrichment)
        entities = extract_entities(text)

        # 2. Match images to entities via OCR'd image text (if any images were submitted)
        image_links = []
        if image_files:
            image_links = match_images_to_entities(image_files, entities)
        entities["image_links"] = image_links

        # 3. Store image file metadata in the job record so commit can use it
        entities["_image_files"] = [
            {"filename": f["filename"], "saved_as": f["saved_as"], "mime": f["mime"]}
            for f in image_files
        ]

        # 4. Save results. Column is named claude_output for historical/schema-
        #    compatibility reasons — it now holds output from the offline
        #    spaCy-based pipeline, not Claude.
        with db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE nlp_jobs
                SET claude_output = %s, status = 'reviewed'
                WHERE id = %s
            """, (json.dumps(entities), job_id))

        logger.info("NLP job %d completed: %d persons, %d groups, %d locations, %d activities, %d image links",
                    job_id,
                    len(entities.get("persons", [])),
                    len(entities.get("groups", [])),
                    len(entities.get("locations", [])),
                    len(entities.get("activities", [])),
                    len(image_links))

    except Exception:
        logger.error("NLP job %d failed:\n%s", job_id, traceback.format_exc())
        with db_cursor(commit=True) as cur:
            cur.execute("""
                UPDATE nlp_jobs SET status = 'failed',
                claude_output = %s WHERE id = %s
            """, (json.dumps({"error": traceback.format_exc()}), job_id))


# ─────────────────────────────────────────────────────────────────────────────
# Commit — write entities to the database
# ─────────────────────────────────────────────────────────────────────────────

_ACTIVITY_TYPES = {"MEETING", "MOVEMENT", "COMMUNICATION", "FINANCIAL", "SURVEILLANCE", "OTHER"}
_HOTSPOT_TYPES  = {"MEETING_POINT", "LOGISTICS", "FINANCIAL", "COMMAND", "SURVEILLANCE", "GENERAL"}


def _map_activity_type(raw) -> str:
    v = str(raw or "").strip().upper()
    return v if v in _ACTIVITY_TYPES else "OTHER"


def _map_hotspot_type(raw) -> str:
    v = str(raw or "").strip().upper().replace(" ", "_")
    return v if v in _HOTSPOT_TYPES else "GENERAL"


_HOTSPOT_DEDUP_RADIUS_M = 300  # two hotspots this close are treated as the same place


def _find_nearby_hotspot(lat: float, lng: float, max_meters: float = _HOTSPOT_DEDUP_RADIUS_M):
    """Return an existing hotspot id within `max_meters` of (lat, lng), or None.

    Uses geopandas/shapely for accurate metric distance (points reprojected to
    Web Mercator before measuring) so documents that phrase the same place
    differently ("the Lagos warehouse" vs "Apapa warehouse, Lagos") don't stack
    near-duplicate hotspots a few dozen metres apart. Best-effort: any failure
    (e.g. geopandas not installed) just disables dedup, never blocks commit.
    """
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        return None
    try:
        with db_cursor() as cur:
            cur.execute("SELECT id, lat, lng FROM hotspots")
            rows = cur.fetchall()
        if not rows:
            return None
        gdf = gpd.GeoDataFrame(
            rows, geometry=[Point(r["lng"], r["lat"]) for r in rows], crs="EPSG:4326"
        ).to_crs(epsg=3857)
        target = gpd.GeoSeries([Point(lng, lat)], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]
        distances = gdf.geometry.distance(target)
        nearest_idx = distances.idxmin()
        if distances[nearest_idx] <= max_meters:
            return int(gdf.loc[nearest_idx, "id"])
        return None
    except Exception as e:
        logger.warning("Hotspot proximity dedup skipped: %s", e)
        return None


def _ensure_hotspot(name: str, htype: str, hit: dict, note) -> int | None:
    """Create a map hotspot for a geocoded location, unless one with the same
    name — or one within ~300m (see _find_nearby_hotspot) — already exists,
    so re-committing (or a differently-worded mention of the same place)
    never stacks duplicate hotspots.
    Requires coordinates — only called when geocode() resolved the place.
    Returns the new hotspot id, or None if a matching one already existed."""
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM hotspots WHERE name = %s LIMIT 1", (name,))
        if cur.fetchone():
            return None
    if _find_nearby_hotspot(hit["lat"], hit["lng"]) is not None:
        return None
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO hotspots (name, type, risk, lat, lng, note)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (name, htype, "MEDIUM", hit["lat"], hit["lng"], note))
        return cur.fetchone()["id"]


def _pin_location(location_id: int, hit: dict) -> bool:
    """Auto-pin a committed location from an offline geocode hit.

    Inserts one row into location_coords only if the location has no
    coordinates yet, so re-committing a duplicate location never stacks pins.
    Returns True when a pin was written.
    """
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT 1 FROM location_coords WHERE location_id = %s LIMIT 1", (location_id,))
        if cur.fetchone():
            return False
        cur.execute(
            "INSERT INTO location_coords (location_id, lat, lng, label) VALUES (%s, %s, %s, %s)",
            (location_id, hit["lat"], hit["lng"], f"auto-geocoded ({hit['confidence']})"),
        )
    return True


def _apply_selections(data: dict, selections: dict | None) -> dict:
    """Filter extracted entities down to only the analyst-selected items
    before committing. `selections` is {"persons":[0,2], "groups":[0], ...} —
    lists of indices into the corresponding array in `data`, as the analyst
    checked them in the review screen. None means "everything" (unfiltered),
    kept for backward compatibility / API callers that don't select.
    """
    if not selections:
        return data

    def pick(key):
        items = data.get(key) or []
        idx = selections.get(key)
        if idx is None:
            return items
        return [items[i] for i in idx if 0 <= i < len(items)]

    persons    = pick("persons")
    groups     = pick("groups")
    activities = pick("activities")
    locations  = pick("locations")

    # Only keep image links pointing at an entity that's still selected —
    # linking a photo to a person/group the analyst deselected would create
    # an orphaned reference to something that's never committed.
    kept_names = {p["name"] for p in persons if p.get("name")} | \
                 {g["name"] for g in groups if g.get("name")} | \
                 {l["name"] for l in locations if l.get("name")}
    image_links = [im for im in (data.get("image_links") or [])
                   if im.get("entity_name") in kept_names]

    filtered = dict(data)
    filtered["persons"] = persons
    filtered["groups"] = groups
    filtered["activities"] = activities
    filtered["locations"] = locations
    filtered["image_links"] = image_links
    return filtered


def commit_job(job_id: int, selections: dict | None = None) -> dict:
    """
    Reads the claude_output for a reviewed job and writes the selected
    entities to the DB. `selections` (optional) restricts the commit to only
    the items the analyst checked in the review screen — see
    _apply_selections(). Returns a summary of what was created.
    """
    with db_cursor() as cur:
        cur.execute("SELECT claude_output FROM nlp_jobs WHERE id = %s AND status = 'reviewed'", (job_id,))
        row = cur.fetchone()
    if not row:
        raise ValueError("Job not found or not in reviewed state.")

    data     = _apply_selections(row["claude_output"], selections)
    summary  = {"persons": [], "groups": [], "locations": [], "hotspots": [],
                "activities": [], "image_links": []}

    # ── Persons ──────────────────────────────────────────────────────────────
    poi_name_to_id = {}
    for p in data.get("persons", []):
        alias = (p.get("name") or "").strip()
        if not alias:
            continue
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO poi (alias, nationality, notes)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
            """, (alias, p.get("nationality"), p.get("notes")))
            row2 = cur.fetchone()
            if not row2:
                # Already exists — fetch ID
                cur.execute("SELECT id FROM poi WHERE alias = %s", (alias,))
                row2 = cur.fetchone()
            if row2:
                poi_name_to_id[alias] = row2["id"]
                summary["persons"].append({"name": alias, "id": row2["id"]})

    # ── Groups ───────────────────────────────────────────────────────────────
    group_name_to_id = {}
    for g in data.get("groups", []):
        name = (g.get("name") or "").strip()
        if not name:
            continue
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO groups_of_interest (name, type, description, notes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
            """, (name, g.get("category"), g.get("description"), g.get("notes")))
            row2 = cur.fetchone()
            if not row2:
                cur.execute("SELECT id FROM groups_of_interest WHERE name = %s", (name,))
                row2 = cur.fetchone()
            if row2:
                group_name_to_id[name] = row2["id"]
                summary["groups"].append({"name": name, "id": row2["id"]})

    # ── Locations ────────────────────────────────────────────────────────────
    location_name_to_id = {}
    location_name_to_hit = {}   # name -> geocode hit, so activities/persons/groups below can inherit coordinates
    for l in data.get("locations", []):
        name = (l.get("name") or "").strip()
        if not name:
            continue
        loc_summary = None
        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO locations (name, address, country, notes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
            """, (name, l.get("address"), l.get("country"), l.get("notes")))
            row2 = cur.fetchone()
            if not row2:
                cur.execute("SELECT id FROM locations WHERE name = %s", (name,))
                row2 = cur.fetchone()
            if row2:
                location_name_to_id[name] = row2["id"]
                loc_summary = {"name": name, "id": row2["id"]}
                summary["locations"].append(loc_summary)

        # Auto-pin on the map using the offline gazetteer (no-op if unresolved
        # or if the gazetteer is not loaded — geocode() returns None safely).
        # When a place resolves to coordinates, also surface it as a map hotspot
        # so extracted locations appear on the Activities & Hotspots map.
        if loc_summary:
            hit = geocode(name, country=l.get("country"), address=l.get("address"))
            if hit:
                location_name_to_hit[name] = hit
                if _pin_location(loc_summary["id"], hit):
                    loc_summary["geocoded"] = {
                        "lat": hit["lat"], "lng": hit["lng"], "confidence": hit["confidence"],
                    }
                hs_id = _ensure_hotspot(name, _map_hotspot_type(l.get("type")), hit, l.get("notes"))
                if hs_id:
                    loc_summary["hotspot_id"] = hs_id
                    summary["hotspots"].append({"name": name, "id": hs_id})

    # ── Activities ───────────────────────────────────────────────────────────
    # The activities table models a single primary poi/group link (not a
    # many-to-many join) — pick the first resolved reference of each as primary.
    for a in data.get("activities", []):
        title = (a.get("title") or "").strip()
        if not title:
            continue

        poi_id = None
        for pname in a.get("poi_names", []):
            if pname in poi_name_to_id:
                poi_id = poi_name_to_id[pname]
                break
        group_id = None
        for gname in a.get("group_names", []):
            if gname in group_name_to_id:
                group_id = group_name_to_id[gname]
                break

        description = title
        if a.get("notes"):
            description = f"{title}\n\n{a['notes']}"

        # Inherit coordinates from the matching extracted+geocoded location, if any.
        loc_hit = location_name_to_hit.get((a.get("location_name") or "").strip())
        act_lat = loc_hit["lat"] if loc_hit else None
        act_lng = loc_hit["lng"] if loc_hit else None

        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO activities (poi_id, group_id, type, occurred_on, location, lat, lng, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (poi_id, group_id, _map_activity_type(a.get("type")),
                  a.get("date") or None, a.get("location_name"), act_lat, act_lng, description))
            act_id = cur.fetchone()["id"]

        summary["activities"].append({"title": title, "id": act_id})

        # Best-effort: give the primary person/group a "known location" pin too,
        # but never overwrite coordinates that were already manually plotted.
        if loc_hit and poi_id:
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    UPDATE poi SET last_lat=%s, last_lng=%s
                    WHERE id=%s AND last_lat IS NULL AND last_lng IS NULL
                """, (loc_hit["lat"], loc_hit["lng"], poi_id))
        if loc_hit and group_id:
            with db_cursor(commit=True) as cur:
                cur.execute("""
                    UPDATE groups_of_interest SET base_lat=%s, base_lng=%s
                    WHERE id=%s AND base_lat IS NULL AND base_lng IS NULL
                """, (loc_hit["lat"], loc_hit["lng"], group_id))

    # ── Image links ──────────────────────────────────────────────────────────
    # Stored inline as base64 in the generic `images` table (entity_type/entity_id),
    # matching how the rest of the app stores photos/images.
    image_file_map = {
        f["filename"]: f for f in data.get("_image_files", [])
    }

    ENTITY_TYPE_MAP = {"poi": "person", "group": "group", "location": "location", "activity": "activity"}

    for link in data.get("image_links", []):
        etype   = (link.get("entity_type") or "").lower()
        ename   = (link.get("entity_name") or "").strip()
        fname   = link.get("filename", "")
        reason  = link.get("reason", "")

        if etype not in ENTITY_TYPE_MAP or not ename or fname not in image_file_map:
            continue

        # Resolve entity ID
        entity_id = None
        if etype == "poi":
            entity_id = poi_name_to_id.get(ename)
            if not entity_id:
                with db_cursor() as cur:
                    cur.execute("SELECT id FROM poi WHERE alias = %s", (ename,))
                    r = cur.fetchone()
                    if r: entity_id = r["id"]
        elif etype == "group":
            entity_id = group_name_to_id.get(ename)
            if not entity_id:
                with db_cursor() as cur:
                    cur.execute("SELECT id FROM groups_of_interest WHERE name = %s", (ename,))
                    r = cur.fetchone()
                    if r: entity_id = r["id"]
        elif etype == "location":
            entity_id = location_name_to_id.get(ename)
        elif etype == "activity":
            for a in summary["activities"]:
                if a["title"] == ename:
                    entity_id = a["id"]
                    break

        if not entity_id:
            logger.warning("Image link: could not resolve entity '%s' (%s)", ename, etype)
            continue

        src = NLP_DIR / image_file_map[fname]["saved_as"]
        if not src.exists():
            logger.warning("Image file not found: %s", src)
            continue

        mime = image_file_map[fname].get("mime", "application/octet-stream")
        content_b64 = base64.b64encode(src.read_bytes()).decode("ascii")
        data_uri = f"data:{mime};base64,{content_b64}"

        with db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO images (entity_type, entity_id, content, name, description, mime_type)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (ENTITY_TYPE_MAP[etype], entity_id, data_uri, fname,
                  f"Auto-linked by NLP: {reason}", mime))
            image_id = cur.fetchone()["id"]

        summary["image_links"].append({
            "entity_type": etype, "entity_name": ename,
            "filename": fname, "image_id": image_id
        })

    # Mark job as committed
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE nlp_jobs SET status = 'committed', committed_at = NOW()
            WHERE id = %s
        """, (job_id,))

    return summary
