"""Read-only database helper for the MCP server tools.

Always opens data/campus_customs_new.db in SQLite read-only mode (mode=ro),
so no tool built on top of this can accidentally write to the database.
"""

import sqlite3
from contextlib import contextmanager

from config import DATABASE_PATH


@contextmanager
def read_only_connection():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")
    uri = f"file:{DATABASE_PATH.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def query(sql: str, params: tuple = ()) -> list[dict]:
    with read_only_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


@contextmanager
def write_connection():
    """Writable connection to the SAME working copy (never campus_customs.db).

    No mode=ro here, so this can INSERT/UPDATE, but it still only ever
    points at DATABASE_PATH (data/campus_customs_new.db).
    """
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def execute_write(sql: str, params: tuple = ()) -> int:
    """Run one parameterized write statement, commit, return lastrowid."""
    with write_connection() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
