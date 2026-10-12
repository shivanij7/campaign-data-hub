"""SQLite storage. Plain sqlite3 on purpose: every query is visible and easy to change."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS deliveries (
    id               INTEGER PRIMARY KEY,
    platform         TEXT NOT NULL,
    week_start       TEXT NOT NULL,
    filename         TEXT NOT NULL UNIQUE,   -- natural key => re-ingest replaces, never duplicates
    received         INTEGER NOT NULL DEFAULT 1,   -- 0 = expected but never arrived
    content_hash     TEXT,
    rows_read        INTEGER NOT NULL DEFAULT 0,
    rows_loaded      INTEGER NOT NULL DEFAULT 0,
    rows_quarantined INTEGER NOT NULL DEFAULT 0,
    health           TEXT NOT NULL CHECK (health IN ('pass','warn','fail')),
    ingested_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    id          INTEGER PRIMARY KEY,
    delivery_id INTEGER NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    source_row  INTEGER NOT NULL,
    platform    TEXT NOT NULL,
    campaign    TEXT NOT NULL,
    date        TEXT NOT NULL,               -- ISO yyyy-mm-dd
    spend_usd   REAL NOT NULL,
    impressions INTEGER NOT NULL,
    clicks      INTEGER NOT NULL,
    transforms  TEXT NOT NULL DEFAULT '[]',  -- JSON list: rules applied to produce this row
    UNIQUE (platform, campaign, date)
);
CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics(date);

CREATE TABLE IF NOT EXISTS quarantined_rows (
    id          INTEGER PRIMARY KEY,
    delivery_id INTEGER NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    source_row  INTEGER NOT NULL,
    code        TEXT NOT NULL,
    field       TEXT,
    message     TEXT NOT NULL,
    raw         TEXT
);

CREATE TABLE IF NOT EXISTS quality_checks (
    id          INTEGER PRIMARY KEY,
    delivery_id INTEGER NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    check_name  TEXT NOT NULL,
    level       TEXT NOT NULL CHECK (level IN ('row','file','delivery')),
    status      TEXT NOT NULL CHECK (status IN ('pass','warn','fail')),
    summary     TEXT NOT NULL,
    details     TEXT NOT NULL DEFAULT '{}',  -- JSON
    UNIQUE (delivery_id, check_name)
);
"""


def connect(path=None, check_same_thread: bool = True) -> sqlite3.Connection:
    # The API opens one connection per request but FastAPI may hop threads inside a request.
    conn = sqlite3.connect(str(path or config.DB_PATH), check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Commit on success, roll back on error. One delivery = one transaction (NFR-2)."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
