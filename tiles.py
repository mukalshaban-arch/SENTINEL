"""
SENTINEL – tiles.py
Offline-first raster map-tile provider.

Tile sources, tried in order:
  1. On-disk cache (tiles/{z}/{x}/{y}.png) — anything previously fetched/warmed.
  2. An .mbtiles package (SENTINEL_MBTILES_PATH) — a standard SQLite-based
     offline tile package, downloaded once from a proper source (e.g. a
     regional export from MapTiler/protomaps). This is the recommended path
     for a genuinely offline deployment: no runtime network call, ever, and
     no tile-provider usage-policy exposure.
  3. A live upstream template (SENTINEL_TILE_UPSTREAM), e.g.
       SENTINEL_TILE_UPSTREAM=https://tile.openstreetmap.org/{z}/{x}/{y}.png
     Optional, for one-time cache warming while online (scripts/prefetch_tiles.py)
     against a provider whose terms actually permit it — most public
     "for humans in a browser" tile servers (including OSM's) do not permit
     bulk scripted access; using one against its policy risks the client
     being blocked (as documented in git history of this file).
  4. A neutral placeholder tile — the final fallback, never a network call.
"""

import os
import base64
import hashlib
import logging
import sqlite3
import urllib.request
from pathlib import Path

logger = logging.getLogger("sentinel.tiles")

TILES_DIR = Path(__file__).resolve().parent / "tiles"
UPSTREAM = os.environ.get("SENTINEL_TILE_UPSTREAM", "").strip()
MBTILES_PATH = os.environ.get("SENTINEL_MBTILES_PATH", "").strip()
USER_AGENT = "SENTINEL/1.0 (offline intelligence dashboard; local tile cache)"

# 256x256 dark grid tile shown for cache misses when offline.
_PLACEHOLDER_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAACSklEQVR42u3dwamDUBRF0f0kI8Uu"
    "HFlB+m9J4tgqDIJrFXA/BPZHJ56x7d/grT7V+Tvu+wPzsrrv/mPvT/4H8GYCQAAgABAACAAEAAI"
    "AAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAD+btgHIPsA+X68+9kHAO"
    "8AIAAQAAgABAACAAGAAEAAIAAQAAgABAACAAGAAEAAIAAQAAgABAACAAGAAEAAIAAQAAgABADZB4"
    "DsA7jvvkcgEAAIAAQAAgABgABAACAAEAAIAAQAAgABgABAACAABAACAAGAAEAAIAAQAAgABAACAA"
    "GAAEAAkH0AyD5Avk/vfvYBwDsACAAEAAIAAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAY"
    "AAQAAgABAACAAEAAIAAUD2ASD7AO677xEIBAACQAB+AgQAAgABgABAACAAEAAIAAQAAgABgABAAC"
    "AAEAAIAAQAAgABgABAACAAEAAIAAQAAoDsA0D2Adx3P/sA4B0ABAACAAGAAEAAIAAQAAgABAACAA"
    "GAAEAAIAAQAAgABAACAAGAABCAnwABgABAACAAEAAIAAQA2QeA7APk+/TuZx8AvAOAAEAAIAAQAA"
    "gABAACAAGAAEAAIAAQAAgABAACAAGAAEAAIAAQAAgABAACAAGAAEAAIAAQAGQfALIP4L77HoFAAC"
    "AAEAAIAAQAAgABgAAQAAgABAACAAGAAEAAIAAQAAgABAACAAGAAEAAIAAQAAgABAACAAHAI10ses"
    "UpnvFUZgAAAABJRU5ErkJggg=="
)
PLACEHOLDER = base64.b64decode(_PLACEHOLDER_B64)


def _cache_path(z: int, x: int, y: int) -> Path:
    return TILES_DIR / str(z) / str(x) / f"{y}.png"


def _fetch_upstream(z: int, x: int, y: int):
    """Fetch one tile from the configured upstream and cache it. Returns bytes or None.

    Validates the response before caching: some tile hosts respond to policy
    violations / rate-limiting with HTTP 200 and a "blocked" notice *image*
    instead of a real error code, which a naive save-whatever-came-back
    fetcher will happily cache as if it were a legitimate tile. We reject
    responses that aren't declared as an image, and flag (without caching)
    any response byte-identical to the last rejected/suspect one — a single
    real map tile is essentially never byte-identical to another.
    """
    if not UPSTREAM:
        return None
    url = UPSTREAM.format(z=z, x=x, y=y, s="a")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as r:
            content_type = r.headers.get("Content-Type", "")
            data = r.read()
    except Exception as e:
        logger.warning("upstream tile %d/%d/%d failed: %s", z, x, y, e)
        return None

    if not content_type.startswith("image/"):
        logger.warning("upstream tile %d/%d/%d rejected: Content-Type was %r, not an image "
                        "(likely a blocked/error response) — not caching.", z, x, y, content_type)
        return None

    global _last_response_hash
    digest = hashlib.sha256(data).hexdigest()
    if digest == _last_response_hash:
        logger.warning("upstream tile %d/%d/%d is byte-identical to the previous tile fetched — "
                        "two distinct map tiles are essentially never identical, so this upstream "
                        "is very likely serving a static blocked/error image. Not caching, and you "
                        "should stop this fetch job (the upstream may be rate-limiting/blocking you).",
                        z, x, y)
        _last_response_hash = digest
        return None
    _last_response_hash = digest

    try:
        p = _cache_path(z, x, y)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    except OSError as e:
        logger.warning("could not cache tile %d/%d/%d: %s", z, x, y, e)
    return data


_last_response_hash = None
_mbtiles_conn = None
_mbtiles_load_failed = False


def _get_mbtiles_conn():
    """Lazy, read-only connection to the configured .mbtiles package."""
    global _mbtiles_conn, _mbtiles_load_failed
    if _mbtiles_conn is not None or _mbtiles_load_failed or not MBTILES_PATH:
        return _mbtiles_conn
    try:
        uri = f"file:{Path(MBTILES_PATH).resolve()}?mode=ro"
        _mbtiles_conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        _mbtiles_conn.execute("SELECT 1 FROM tiles LIMIT 1")
        logger.info("MBTiles offline tile package loaded: %s", MBTILES_PATH)
    except Exception as e:
        logger.error("Could not open MBTILES_PATH=%r as a tile package (%s) — "
                      "falling back to other tile sources.", MBTILES_PATH, e)
        _mbtiles_load_failed = True
        _mbtiles_conn = None
    return _mbtiles_conn


def _get_mbtile(z: int, x: int, y: int):
    """MBTiles stores rows with a flipped (TMS) Y axis vs. the XYZ scheme
    Leaflet/this app's /tiles/{z}/{x}/{y}.png route uses — convert before
    querying. Returns bytes or None."""
    conn = _get_mbtiles_conn()
    if conn is None:
        return None
    tms_y = (2 ** z - 1) - y
    try:
        row = conn.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (z, x, tms_y),
        ).fetchone()
        return row[0] if row else None
    except sqlite3.Error as e:
        logger.warning("MBTiles read failed for %d/%d/%d: %s", z, x, y, e)
        return None


def get_tile(z: int, x: int, y: int):
    """Return (png_bytes, hit) for a tile. Never raises.

    Tries, in order: the on-disk cache, an .mbtiles package (if configured),
    a live upstream (if configured), then a neutral placeholder. `hit` is
    True only when the tile came from the local cache or the mbtiles package
    — i.e. no network call was made.
    """
    p = _cache_path(z, x, y)
    if p.exists():
        try:
            return p.read_bytes(), True
        except OSError:
            pass

    data = _get_mbtile(z, x, y)
    if data is not None:
        return data, True

    data = _fetch_upstream(z, x, y)
    if data is not None:
        return data, False
    return PLACEHOLDER, False
