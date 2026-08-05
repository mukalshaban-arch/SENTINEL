"""Unit tests for tiles.py: on-disk cache path/hit, mbtiles TMS y-flip
(against a real temp SQLite mbtiles fixture), and placeholder fallback.
Upstream HTTP fetching is intentionally not exercised here — this module
must never make a real network call in unit tests."""
import sqlite3

import pytest

import tiles


@pytest.fixture(autouse=True)
def _isolated_tile_state(tmp_path, monkeypatch):
    """Every test gets its own empty tile cache dir and no configured
    mbtiles/upstream, so tests can't see each other's cached files or the
    real project's tiles/ directory."""
    monkeypatch.setattr(tiles, "TILES_DIR", tmp_path)
    monkeypatch.setattr(tiles, "UPSTREAM", "")
    monkeypatch.setattr(tiles, "MBTILES_PATH", "")
    monkeypatch.setattr(tiles, "_mbtiles_conn", None)
    monkeypatch.setattr(tiles, "_mbtiles_load_failed", False)
    monkeypatch.setattr(tiles, "_last_response_hash", None)


def test_cache_path_layout(tmp_path):
    p = tiles._cache_path(5, 10, 15)
    assert p == tmp_path / "5" / "10" / "15.png"


def test_get_tile_returns_placeholder_when_nothing_configured():
    data, hit = tiles.get_tile(3, 4, 4)
    assert data == tiles.PLACEHOLDER
    assert hit is False


def test_get_tile_reads_from_disk_cache(tmp_path):
    p = tiles._cache_path(2, 1, 1)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"fake-png-bytes")

    data, hit = tiles.get_tile(2, 1, 1)
    assert data == b"fake-png-bytes"
    assert hit is True


def test_get_tile_disk_cache_takes_priority_over_placeholder(tmp_path):
    # Same tile requested twice — second call must still hit cache, not refetch.
    p = tiles._cache_path(1, 0, 0)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"cached")
    assert tiles.get_tile(1, 0, 0) == (b"cached", True)
    assert tiles.get_tile(1, 0, 0) == (b"cached", True)


def _make_mbtiles(path, rows):
    """rows: list of (zoom, col, tms_row, data) already in TMS convention."""
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE tiles (zoom_level INT, tile_column INT, tile_row INT, tile_data BLOB)")
    conn.executemany("INSERT INTO tiles VALUES (?,?,?,?)", rows)
    conn.commit()
    conn.close()


def test_get_tile_reads_from_mbtiles_with_tms_y_flip(tmp_path, monkeypatch):
    mbtiles_path = tmp_path / "region.mbtiles"
    z = 3
    xyz_y = 2  # the y this app's route uses (XYZ scheme)
    tms_y = (2 ** z - 1) - xyz_y
    _make_mbtiles(mbtiles_path, [(z, 5, tms_y, b"mbtiles-tile-bytes")])

    monkeypatch.setattr(tiles, "MBTILES_PATH", str(mbtiles_path))

    data, hit = tiles.get_tile(z, 5, xyz_y)
    assert data == b"mbtiles-tile-bytes"
    assert hit is True


def test_get_tile_mbtiles_miss_falls_through_to_placeholder(tmp_path, monkeypatch):
    mbtiles_path = tmp_path / "region.mbtiles"
    _make_mbtiles(mbtiles_path, [])  # empty table — valid package, no matching tile
    monkeypatch.setattr(tiles, "MBTILES_PATH", str(mbtiles_path))

    data, hit = tiles.get_tile(9, 9, 9)
    assert data == tiles.PLACEHOLDER
    assert hit is False


def test_get_mbtiles_conn_handles_missing_file_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(tiles, "MBTILES_PATH", str(tmp_path / "does_not_exist.mbtiles"))
    assert tiles._get_mbtiles_conn() is None
    assert tiles._mbtiles_load_failed is True
