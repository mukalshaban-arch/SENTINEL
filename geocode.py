"""
SENTINEL – geocode.py
Offline place-name → coordinate lookup against the local `gazetteer` table
(populated from GeoNames data via scripts/load_gazetteer.py).

Fully offline: no network calls, ever. Returns None when a name cannot be
resolved — it never guesses — so callers can leave unresolved locations
unpinned rather than dropping a marker in the wrong place.
"""

import logging
import unicodedata

from db import db_cursor

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Lower-case, strip accents, collapse whitespace.

    Must match how the loader builds `gazetteer.search_key`, so that lookups
    are accent- and case-insensitive (e.g. "Zürich" == "zurich").
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def _lookup(key: str, country: str | None = None):
    """Return the best gazetteer row for `key`, or None. Highest population wins."""
    sql = "SELECT lat, lng, name, country, population FROM gazetteer WHERE search_key = %s "
    params = [key]
    if country:
        sql += "AND country ILIKE %s "
        params.append(f"%{country.strip()}%")
    sql += "ORDER BY population DESC NULLS LAST LIMIT 1"
    with db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def geocode(name: str, country: str | None = None, address: str | None = None):
    """
    Resolve a place name to coordinates using the offline gazetteer.

    Returns {"lat", "lng", "confidence", "matched_name", "country"} or None.
      - country: optional free-text hint used to disambiguate same-named places.
      - address: optional; its first comma-separated part is tried if `name` misses.
      - confidence: "high" when a country hint narrowed the match, else "medium".

    Never raises. On any error (e.g. the gazetteer has not been loaded yet) it
    returns None, so ingestion is never blocked by a missing/empty gazetteer.
    """
    key = _normalize(name)
    if not key:
        return None
    try:
        row = None
        confidence = "medium"
        if country:
            row = _lookup(key, country)
            if row:
                confidence = "high"
        if not row:
            row = _lookup(key, None)
        if not row and address:
            first = _normalize(address.split(",")[0])
            if first and first != key:
                row = _lookup(first, country) or _lookup(first, None)
        if not row:
            return None
        return {
            "lat": row["lat"],
            "lng": row["lng"],
            "confidence": confidence,
            "matched_name": row["name"],
            "country": row["country"],
        }
    except Exception as e:  # gazetteer table missing, DB hiccup, etc.
        logger.warning("geocode(%r) failed — leaving unpinned: %s", name, e)
        return None
