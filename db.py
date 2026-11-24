import os
import sqlite3
from contextlib import closing

import config


def _connect(db_path=None):
    db_path = db_path or config.DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path=None):
    with closing(_connect(db_path)) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                name TEXT,
                version TEXT,
                online INTEGER,
                uptime_seconds REAL,
                last_seen INTEGER,
                recorded_at INTEGER
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_recorded_at ON history(recorded_at)")


def log_history(entries, recorded_at, db_path=None):
    """Append one row per server."""
    rows = [
        (
            e.get("address"),
            e.get("name"),
            e.get("version"),
            1 if e.get("online") else 0,
            float(e.get("uptime_seconds") or 0),
            int(e["last_seen"]) if e.get("last_seen") is not None else None,
            int(recorded_at),
        )
        for e in entries
    ]
    with closing(_connect(db_path)) as conn, conn:
        conn.executemany(
            """
            INSERT INTO history (address, name, version, online, uptime_seconds, last_seen, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def prune_before(cutoff_ms, db_path=None):
    """Delete history older than `cutoff_ms` so the database doesn't grow forever."""
    with closing(_connect(db_path)) as conn, conn:
        conn.execute("DELETE FROM history WHERE recorded_at < ?", (int(cutoff_ms),))


def fetch_history_since(since_ms, db_path=None):
    """Return [{address, online, recorded_at}] for rows recorded since `since_ms`."""
    db_path = db_path or config.DB_PATH
    if not os.path.exists(db_path):
        return []
    with closing(_connect(db_path)) as conn:
        cur = conn.execute(
            "SELECT address, online, recorded_at FROM history WHERE recorded_at >= ? ORDER BY recorded_at",
            (int(since_ms),),
        )
        return [
            {"address": a, "online": bool(o), "recorded_at": int(r)}
            for a, o, r in cur.fetchall()
        ]
