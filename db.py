"""
SENTINEL – db.py
Centralised PostgreSQL connection pool.
All other modules import `get_conn` / `release_conn` from here.

Environment variables (set in .env or system environment):
    SENTINEL_DB_HOST     default: localhost
    SENTINEL_DB_PORT     default: 5432
    SENTINEL_DB_NAME     default: sentinel
    SENTINEL_DB_USER     default: sentinel_user
    SENTINEL_DB_PASS     (required – no default)
    SENTINEL_DB_MINCONN  default: 2
    SENTINEL_DB_MAXCONN  default: 10
"""

import os
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_pool: pool.ThreadedConnectionPool | None = None


def init_pool() -> None:
    """Call once at server startup."""
    global _pool
    _pool = pool.ThreadedConnectionPool(
        minconn=int(os.environ.get("SENTINEL_DB_MINCONN", 2)),
        maxconn=int(os.environ.get("SENTINEL_DB_MAXCONN", 10)),
        host=os.environ.get("SENTINEL_DB_HOST", "localhost"),
        port=int(os.environ.get("SENTINEL_DB_PORT", 5432)),
        dbname=os.environ.get("SENTINEL_DB_NAME", "sentinel"),
        user=os.environ.get("SENTINEL_DB_USER", "sentinel_user"),
        password=os.environ["SENTINEL_DB_PASS"],   # intentional – fail fast
        cursor_factory=RealDictCursor,
        connect_timeout=5,
    )
    logger.info("PostgreSQL connection pool initialised.")


def close_pool() -> None:
    if _pool:
        _pool.closeall()
        logger.info("PostgreSQL connection pool closed.")


def get_conn():
    if _pool is None:
        raise RuntimeError("DB pool not initialised – call init_pool() first.")
    return _pool.getconn()


def release_conn(conn, discard: bool = False) -> None:
    if _pool and conn:
        _pool.putconn(conn, close=discard)


@contextmanager
def db_cursor(commit: bool = False):
    """
    Context manager that yields a (conn, cursor) pair.
    Automatically commits/rolls-back and returns the connection to the pool.

    Usage:
        with db_cursor(commit=True) as cur:
            cur.execute("INSERT INTO poi ...")
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_conn(conn)
