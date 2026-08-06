"""Unit tests for db.py's pool lifecycle and the db_cursor context manager.

psycopg2's pool is stubbed — this covers the transaction semantics every
other module relies on: commit only when asked, rollback on exception, and
the connection always returned to the pool.
"""
from unittest.mock import MagicMock

import pytest

import db


@pytest.fixture
def fake_pool(monkeypatch):
    pool = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    # `with conn.cursor() as cur:` -> cursor
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    pool.getconn.return_value = conn
    monkeypatch.setattr(db, "_pool", pool)
    return pool, conn, cursor


# ── Pool lifecycle ────────────────────────────────────────────────────────
def test_get_conn_raises_when_pool_uninitialised(monkeypatch):
    monkeypatch.setattr(db, "_pool", None)
    with pytest.raises(RuntimeError, match="not initialised"):
        db.get_conn()


def test_get_conn_returns_pooled_connection(fake_pool):
    pool, conn, _ = fake_pool
    assert db.get_conn() is conn
    pool.getconn.assert_called_once()


def test_release_conn_returns_to_pool(fake_pool):
    pool, conn, _ = fake_pool
    db.release_conn(conn)
    pool.putconn.assert_called_once_with(conn, close=False)


def test_release_conn_can_discard(fake_pool):
    pool, conn, _ = fake_pool
    db.release_conn(conn, discard=True)
    pool.putconn.assert_called_once_with(conn, close=True)


def test_release_conn_is_a_noop_without_a_connection(fake_pool):
    pool, _, _ = fake_pool
    db.release_conn(None)
    pool.putconn.assert_not_called()


def test_close_pool_closes_all(fake_pool):
    pool, _, _ = fake_pool
    db.close_pool()
    pool.closeall.assert_called_once()


def test_close_pool_is_safe_when_uninitialised(monkeypatch):
    monkeypatch.setattr(db, "_pool", None)
    db.close_pool()  # must not raise


def test_init_pool_reads_settings_from_environment(monkeypatch):
    captured = {}

    class FakeThreadedPool:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(db.pool, "ThreadedConnectionPool", FakeThreadedPool)
    monkeypatch.setenv("SENTINEL_DB_HOST", "dbhost")
    monkeypatch.setenv("SENTINEL_DB_PORT", "6543")
    monkeypatch.setenv("SENTINEL_DB_NAME", "testdb")
    monkeypatch.setenv("SENTINEL_DB_USER", "testuser")
    monkeypatch.setenv("SENTINEL_DB_PASS", "testpass")
    monkeypatch.setenv("SENTINEL_DB_MINCONN", "3")
    monkeypatch.setenv("SENTINEL_DB_MAXCONN", "9")

    db.init_pool()

    assert captured["host"] == "dbhost"
    assert captured["port"] == 6543
    assert captured["dbname"] == "testdb"
    assert captured["user"] == "testuser"
    assert captured["password"] == "testpass"
    assert captured["minconn"] == 3
    assert captured["maxconn"] == 9


def test_init_pool_fails_fast_without_a_password(monkeypatch):
    monkeypatch.setattr(db.pool, "ThreadedConnectionPool", lambda **kw: None)
    monkeypatch.delenv("SENTINEL_DB_PASS", raising=False)
    # Intentional KeyError — a missing password must not silently default.
    with pytest.raises(KeyError):
        db.init_pool()


# ── db_cursor transaction semantics ──────────────────────────────────────
def test_db_cursor_yields_a_cursor_and_releases_the_connection(fake_pool):
    pool, conn, cursor = fake_pool
    with db.db_cursor() as cur:
        assert cur is cursor
    pool.putconn.assert_called_once()


def test_db_cursor_does_not_commit_by_default(fake_pool):
    _, conn, _ = fake_pool
    with db.db_cursor():
        pass
    conn.commit.assert_not_called()


def test_db_cursor_commits_when_asked(fake_pool):
    _, conn, _ = fake_pool
    with db.db_cursor(commit=True):
        pass
    conn.commit.assert_called_once()


def test_db_cursor_rolls_back_and_reraises_on_error(fake_pool):
    pool, conn, _ = fake_pool
    with pytest.raises(ValueError):
        with db.db_cursor(commit=True):
            raise ValueError("query blew up")
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
    pool.putconn.assert_called_once()   # still returned to the pool


def test_db_cursor_releases_connection_even_when_commit_fails(fake_pool):
    pool, conn, _ = fake_pool
    conn.commit.side_effect = RuntimeError("commit failed")
    with pytest.raises(RuntimeError):
        with db.db_cursor(commit=True):
            pass
    conn.rollback.assert_called_once()
    pool.putconn.assert_called_once()
