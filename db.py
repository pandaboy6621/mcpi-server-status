import sqlite3
import os


def init_db(db_path='status.db'):
    dirpath = os.path.dirname(db_path)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
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
    ''')
    conn.commit()
    conn.close()


def log_history(entries, recorded_at, db_path='status.db'):
    """Append a row per server to the history table."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    for e in entries:
        c.execute('''
        INSERT INTO history (address, name, version, online, uptime_seconds, last_seen, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            e.get('address'),
            e.get('name'),
            e.get('version'),
            1 if e.get('online') else 0,
            float(e.get('uptime_seconds') or 0),
            int(e.get('last_seen')) if e.get('last_seen') is not None else None,
            int(recorded_at),
        ))
    conn.commit()
    conn.close()


def fetch_history_since(since_ms, db_path='status.db'):
    """Return list of history rows since `since_ms` (ms epoch).

    Each row is a dict: {address, online, recorded_at}.
    """
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
    SELECT address, online, recorded_at FROM history
    WHERE recorded_at >= ?
    ORDER BY recorded_at ASC
    ''', (int(since_ms),))
    rows = []
    for address, online, recorded_at in c.fetchall():
        rows.append({
            'address': address,
            'online': bool(online),
            'recorded_at': int(recorded_at),
        })
    conn.close()
    return rows
