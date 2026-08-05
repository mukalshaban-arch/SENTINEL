"""
SENTINEL – scripts/load_gazetteer.py
One-time loader that imports GeoNames data into the offline `gazetteer` table
used by geocode.py.

GeoNames data (https://download.geonames.org/export/dump/) is a tab-separated
dump with 19 columns per row. Download the file(s) for your area of operations
— per-country (e.g. NG.txt, KE.txt) or a bulk file — plus countryInfo.txt so
ISO country codes become full names (which is what the app stores in
locations.country).

Usage (run from the SENTINEL project root, offline is fine):
    python scripts/load_gazetteer.py NG.txt KE.txt ET.txt \\
        --country-info countryInfo.txt --replace

Options:
    --country-info FILE   GeoNames countryInfo.txt (maps ISO2 -> country name)
    --feature-classes CSV Feature classes to keep (default "P,A":
                          P = populated places, A = admin regions)
    --min-pop N           Skip places with population < N (default 0)
    --replace             TRUNCATE the table before loading
    --batch N             Rows per INSERT batch (default 5000)
"""

import sys
import csv
import argparse
from pathlib import Path

# Make the project root importable when run as `python scripts/load_gazetteer.py`.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from psycopg2.extras import execute_values

import db
from geocode import _normalize

# GeoNames dump column indices (0-based).
COL_GEONAMEID, COL_NAME, COL_ASCII = 0, 1, 2
COL_LAT, COL_LNG = 4, 5
COL_FCLASS, COL_FCODE, COL_CC = 6, 7, 8
COL_ADMIN1, COL_POP = 10, 14

DDL = """
CREATE TABLE IF NOT EXISTS gazetteer (
    id           SERIAL PRIMARY KEY,
    geonameid    BIGINT,
    name         TEXT NOT NULL,
    asciiname    TEXT,
    search_key   TEXT NOT NULL,
    country      TEXT,
    admin1       TEXT,
    lat          DOUBLE PRECISION NOT NULL,
    lng          DOUBLE PRECISION NOT NULL,
    population   BIGINT DEFAULT 0,
    feature_code TEXT
);
CREATE INDEX IF NOT EXISTS idx_gazetteer_search_key ON gazetteer (search_key);
CREATE INDEX IF NOT EXISTS idx_gazetteer_key_country ON gazetteer (search_key, country);
"""

INSERT_SQL = (
    "INSERT INTO gazetteer "
    "(geonameid, name, asciiname, search_key, country, admin1, lat, lng, population, feature_code) "
    "VALUES %s"
)


def _load_dotenv() -> None:
    """Mirror server.py's tiny .env loader so this script runs standalone."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    import os
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def load_country_names(path: Path) -> dict:
    """Parse GeoNames countryInfo.txt into {ISO2: country name}."""
    mapping = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) > 4 and cols[0]:
            mapping[cols[0]] = cols[4]
    return mapping


def iter_rows(path: Path, keep_classes: set, min_pop: int, cc_names: dict):
    """Yield insert tuples for the gazetteer table from one GeoNames dump."""
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        for row in reader:
            if len(row) < 15:
                continue
            if keep_classes and row[COL_FCLASS] not in keep_classes:
                continue
            try:
                pop = int(row[COL_POP] or 0)
            except ValueError:
                pop = 0
            if pop < min_pop:
                continue
            try:
                lat = float(row[COL_LAT])
                lng = float(row[COL_LNG])
            except ValueError:
                continue
            name = row[COL_NAME]
            ascii_name = row[COL_ASCII] or name
            search_key = _normalize(ascii_name)
            if not search_key:
                continue
            cc = row[COL_CC]
            country = cc_names.get(cc, cc)
            yield (
                int(row[COL_GEONAMEID]) if row[COL_GEONAMEID].isdigit() else None,
                name, ascii_name, search_key, country, row[COL_ADMIN1],
                lat, lng, pop, row[COL_FCODE],
            )


def main() -> None:
    ap = argparse.ArgumentParser(description="Load GeoNames data into the gazetteer table.")
    ap.add_argument("files", nargs="+", help="GeoNames dump file(s), e.g. NG.txt KE.txt")
    ap.add_argument("--country-info", type=Path, help="GeoNames countryInfo.txt (ISO2 -> name)")
    ap.add_argument("--feature-classes", default="P,A", help='Feature classes to keep (default "P,A")')
    ap.add_argument("--min-pop", type=int, default=0, help="Skip places below this population")
    ap.add_argument("--replace", action="store_true", help="TRUNCATE the table before loading")
    ap.add_argument("--batch", type=int, default=5000, help="Rows per INSERT batch")
    args = ap.parse_args()

    keep_classes = {c.strip() for c in args.feature_classes.split(",") if c.strip()}
    cc_names = load_country_names(args.country_info) if args.country_info else {}
    if args.country_info:
        print(f"Loaded {len(cc_names)} country names from {args.country_info}")

    _load_dotenv()
    db.init_pool()

    with db.db_cursor(commit=True) as cur:
        cur.execute(DDL)
        if args.replace:
            cur.execute("TRUNCATE gazetteer RESTART IDENTITY")
            print("Truncated existing gazetteer.")

    total = 0
    batch = []
    for f in args.files:
        path = Path(f)
        if not path.exists():
            print(f"! skipping missing file: {path}")
            continue
        print(f"Reading {path} ...")
        for rec in iter_rows(path, keep_classes, args.min_pop, cc_names):
            batch.append(rec)
            if len(batch) >= args.batch:
                with db.db_cursor(commit=True) as cur:
                    execute_values(cur, INSERT_SQL, batch, page_size=1000)
                total += len(batch)
                batch.clear()
                print(f"  ... {total:,} rows", end="\r")
    if batch:
        with db.db_cursor(commit=True) as cur:
            execute_values(cur, INSERT_SQL, batch, page_size=1000)
        total += len(batch)

    db.close_pool()
    print(f"\nDone. Loaded {total:,} gazetteer rows.")


if __name__ == "__main__":
    main()
