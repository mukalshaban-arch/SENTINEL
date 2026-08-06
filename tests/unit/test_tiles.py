"""Unit tests for tiles.py: on-disk cache path/hit, mbtiles TMS y-flip
(against a real temp SQLite mbtiles fixture), and placeholder fallback.
Upstream HTTP fetching is intentionally not exercised here — this module
must never make a real network call in unit tests."""
import sqlite3
from pathlib import Path

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


# ── _fetch_upstream (network stubbed — never a real request) ─────────────
class FakeResponse:
    def __init__(self, data, content_type="image/png"):
        self._data = data
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_urlopen(monkeypatch, response=None, raises=None):
    import urllib.request

    def fake_urlopen(req, timeout=None):
        if raises:
            raise raises
        return response

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def test_fetch_upstream_returns_none_when_not_configured(monkeypatch):
    monkeypatch.setattr(tiles, "UPSTREAM", "")
    assert tiles._fetch_upstream(1, 2, 3) is None


def test_fetch_upstream_caches_a_valid_tile(monkeypatch, tmp_path):
    monkeypatch.setattr(tiles, "UPSTREAM", "https://example.invalid/{z}/{x}/{y}.png")
    _patch_urlopen(monkeypatch, FakeResponse(b"real-tile-bytes"))

    data = tiles._fetch_upstream(2, 3, 4)
    assert data == b"real-tile-bytes"
    assert tiles._cache_path(2, 3, 4).read_bytes() == b"real-tile-bytes"


def test_fetch_upstream_returns_none_on_network_error(monkeypatch):
    monkeypatch.setattr(tiles, "UPSTREAM", "https://example.invalid/{z}/{x}/{y}.png")
    _patch_urlopen(monkeypatch, raises=OSError("connection refused"))
    assert tiles._fetch_upstream(1, 1, 1) is None


def test_fetch_upstream_rejects_non_image_content_type(monkeypatch):
    """A tile host that answers a policy block with HTTP 200 + an HTML notice
    must not have that response cached as if it were a map tile."""
    monkeypatch.setattr(tiles, "UPSTREAM", "https://example.invalid/{z}/{x}/{y}.png")
    _patch_urlopen(monkeypatch, FakeResponse(b"<html>blocked</html>", "text/html"))

    assert tiles._fetch_upstream(1, 1, 1) is None
    assert not tiles._cache_path(1, 1, 1).exists()


def test_fetch_upstream_rejects_byte_identical_consecutive_tiles(monkeypatch):
    """Two distinct map tiles are essentially never byte-identical — an exact
    repeat signals a static 'blocked' image being served for every request."""
    monkeypatch.setattr(tiles, "UPSTREAM", "https://example.invalid/{z}/{x}/{y}.png")
    _patch_urlopen(monkeypatch, FakeResponse(b"same-bytes-every-time"))

    first = tiles._fetch_upstream(5, 1, 1)
    second = tiles._fetch_upstream(5, 2, 2)

    assert first == b"same-bytes-every-time"
    assert second is None
    assert not tiles._cache_path(5, 2, 2).exists()


def test_fetch_upstream_allows_differing_consecutive_tiles(monkeypatch):
    monkeypatch.setattr(tiles, "UPSTREAM", "https://example.invalid/{z}/{x}/{y}.png")
    import urllib.request

    responses = [FakeResponse(b"tile-one"), FakeResponse(b"tile-two")]
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=None: responses.pop(0))

    assert tiles._fetch_upstream(6, 1, 1) == b"tile-one"
    assert tiles._fetch_upstream(6, 2, 2) == b"tile-two"


def test_get_tile_uses_upstream_and_reports_it_as_a_miss(monkeypatch):
    monkeypatch.setattr(tiles, "UPSTREAM", "https://example.invalid/{z}/{x}/{y}.png")
    _patch_urlopen(monkeypatch, FakeResponse(b"fetched-tile"))

    data, hit = tiles.get_tile(7, 7, 7)
    assert data == b"fetched-tile"
    assert hit is False   # a network call was made, so not a local hit


# ── Error branches ────────────────────────────────────────────────────────
def test_get_tile_falls_through_when_cached_file_is_unreadable(monkeypatch, tmp_path):
    p = tiles._cache_path(4, 4, 4)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"cached")

    def boom(self, *a, **kw):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "read_bytes", boom)
    data, hit = tiles.get_tile(4, 4, 4)
    assert data == tiles.PLACEHOLDER
    assert hit is False


def test_fetch_upstream_still_returns_data_when_caching_fails(monkeypatch):
    monkeypatch.setattr(tiles, "UPSTREAM", "https://example.invalid/{z}/{x}/{y}.png")
    _patch_urlopen(monkeypatch, FakeResponse(b"tile-bytes"))

    def boom(self, *a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_bytes", boom)
    # The tile is still served to the caller even though it could not be cached.
    assert tiles._fetch_upstream(8, 8, 8) == b"tile-bytes"


def test_get_mbtile_returns_none_on_sqlite_error(monkeypatch, tmp_path):
    import sqlite3

    class BadConn:
        def execute(self, *a, **kw):
            raise sqlite3.Error("database is locked")

    monkeypatch.setattr(tiles, "_get_mbtiles_conn", lambda: BadConn())
    assert tiles._get_mbtile(1, 1, 1) is None


def test_get_mbtiles_conn_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.setattr(tiles, "MBTILES_PATH", "")
    assert tiles._get_mbtiles_conn() is None
