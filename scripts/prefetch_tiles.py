"""
SENTINEL – scripts/prefetch_tiles.py
Warm the offline tile cache (tiles/{z}/{x}/{y}.png) for an area of operations,
WHILE ONLINE. Run this deliberately for the regions you need; do not bulk-fetch
whole continents from OSM's public servers (against their usage policy).

Usage (from the SENTINEL project root):
    python scripts/prefetch_tiles.py --bbox <minLon> <minLat> <maxLon> <maxLat> \\
        --zoom 3 9 --upstream https://tile.openstreetmap.org/{z}/{x}/{y}.png

Notes:
  - --upstream may be omitted if SENTINEL_TILE_UPSTREAM is set (e.g. in .env).
  - A polite delay between requests is applied by default.
  - Prints an estimate first and refuses very large jobs unless --yes is given.
"""

import sys
import math
import time
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tiles


def deg2num(lat: float, lon: float, z: int):
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def tile_ranges(bbox, z):
    min_lon, min_lat, max_lon, max_lat = bbox
    x0, y0 = deg2num(max_lat, min_lon, z)   # top-left  (max lat -> smaller y)
    x1, y1 = deg2num(min_lat, max_lon, z)   # bottom-right
    return range(min(x0, x1), max(x0, x1) + 1), range(min(y0, y1), max(y0, y1) + 1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Warm the offline map-tile cache for a bounding box.")
    ap.add_argument("--bbox", nargs=4, type=float, required=True,
                    metavar=("minLon", "minLat", "maxLon", "maxLat"))
    ap.add_argument("--zoom", nargs=2, type=int, default=[3, 9], metavar=("MINZ", "MAXZ"))
    ap.add_argument("--upstream", help="Tile URL template; overrides SENTINEL_TILE_UPSTREAM")
    ap.add_argument("--delay", type=float, default=0.1, help="Seconds between requests (default 0.1)")
    ap.add_argument("--yes", action="store_true", help="Proceed even for large jobs")
    args = ap.parse_args()

    if args.upstream:
        tiles.UPSTREAM = args.upstream.strip()
    if not tiles.UPSTREAM:
        sys.exit("No upstream configured. Pass --upstream or set SENTINEL_TILE_UPSTREAM.")

    zmin, zmax = args.zoom
    total = sum(len(tile_ranges(args.bbox, z)[0]) * len(tile_ranges(args.bbox, z)[1])
                for z in range(zmin, zmax + 1))
    print(f"Estimated tiles to fetch (z{zmin}-{zmax}): {total:,}")
    if total > 50_000 and not args.yes:
        sys.exit("Refusing >50,000 tiles without --yes (respect OSM tile-usage policy). "
                 "Narrow the bbox/zoom or pass --yes.")

    done = fetched = rejected_streak = 0
    ABORT_AFTER = 5   # consecutive rejected/suspect responses -> the upstream is blocking us
    for z in range(zmin, zmax + 1):
        xs, ys = tile_ranges(args.bbox, z)
        for x in xs:
            for y in ys:
                done += 1
                if tiles._cache_path(z, x, y).exists():
                    continue
                if tiles._fetch_upstream(z, x, y) is not None:
                    fetched += 1
                    rejected_streak = 0
                else:
                    rejected_streak += 1
                    if rejected_streak >= ABORT_AFTER:
                        sys.exit(f"\nAborting: {ABORT_AFTER} tile fetches in a row were rejected "
                                 f"(bad content-type or duplicate/blocked-image content). The "
                                 f"upstream is very likely rate-limiting or blocking this client per "
                                 f"its usage policy. Fetched {fetched:,} good tiles before this — "
                                 f"wait before retrying, and confirm you're within the provider's "
                                 f"usage policy.")
                time.sleep(args.delay)
                if done % 200 == 0:
                    print(f"  {done:,}/{total:,} (fetched {fetched:,})", end="\r")
    print(f"\nDone. Checked {done:,} tiles, fetched {fetched:,} new into {tiles.TILES_DIR}.")


if __name__ == "__main__":
    main()
