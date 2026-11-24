"""Shared paths and settings. Everything can be overridden with environment variables."""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.abspath(os.environ.get("MCPI_DATA_DIR", os.path.join(BASE_DIR, "data")))
STATUS_PATH = os.path.join(DATA_DIR, "status.json")
DB_PATH = os.path.join(DATA_DIR, "status.db")
SERVERS_PATH = os.environ.get("MCPI_SERVERS_FILE", os.path.join(BASE_DIR, "servers.json"))

PING_INTERVAL = float(os.environ.get("MCPI_PING_INTERVAL", "30"))
PING_TIMEOUT = float(os.environ.get("MCPI_PING_TIMEOUT", "5"))
HISTORY_DAYS = int(os.environ.get("MCPI_HISTORY_DAYS", "7"))


def load_servers(path=None):
    """Read the server list. Entries may be plain address strings or dicts."""
    with open(path or SERVERS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    servers = []
    for entry in raw:
        if isinstance(entry, str):
            entry = {"address": entry}
        if not entry.get("address"):
            continue
        servers.append(entry)
    return servers
