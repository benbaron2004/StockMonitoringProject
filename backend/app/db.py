from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    ticker_a TEXT,
    ticker_b TEXT,
    baseline_price_a REAL,
    baseline_price_b REAL,
    current_price_a REAL,
    current_price_b REAL,
    threshold_pct REAL,
    alerted INTEGER NOT NULL DEFAULT 0,
    alerted_at TEXT,
    started_at TEXT,
    stopped_at TEXT,
    last_updated_at TEXT,
    last_poll_error TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    conn.commit()
    return conn
