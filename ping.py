"""Ping MCPI (RakNet) servers and record their status.

Run once:        python ping.py
Run forever:     python ping.py --loop
(app.py runs this loop for you in a background thread, so you normally don't need to.)
"""
import argparse
import json
import os
import random
import re
import socket
import struct
import time
from concurrent.futures import ThreadPoolExecutor

import config
import db

DEFAULT_PORT = 19132
RAKNET_MAGIC = b"\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78"
UNCONNECTED_PING_OPEN = 0x02
UNCONNECTED_PONG = 0x1C
PLAYERS_RE = re.compile(r"\s*[-|(]?\s*(\d+)\s+connected players\)?", re.IGNORECASE)


def split_address(address):
    if ":" in address:
        host, port = address.rsplit(":", 1)
        return host, int(port)
    return address, DEFAULT_PORT


def parse_pong(data):
    """Return the server info string ("MCCPP;Demo;Name") from an unconnected pong, or None."""
    # id(1) + time(8) + guid(8) + magic(16) + strlen(2) + string
    if len(data) < 35 or data[0] != UNCONNECTED_PONG:
        return None
    (length,) = struct.unpack_from(">H", data, 33)
    return data[35:35 + length].decode("utf-8", errors="replace")


def get_server_status(address, timeout=None):
    """Ping one server. Returns {online, name, players} (name/players may be None)."""
    timeout = timeout or config.PING_TIMEOUT
    result = {"online": False, "name": None, "players": None}
    try:
        host, port = split_address(address)
        family, _, _, _, sockaddr = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)[0]
        # Same packet the original checker used (0x02 = "unconnected ping, open connections").
        packet = bytes([UNCONNECTED_PING_OPEN]) + struct.pack(">q", random.randint(1, 2**31)) + RAKNET_MAGIC
        with socket.socket(family, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, sockaddr)
            data, _ = sock.recvfrom(2048)
    except (OSError, ValueError):
        return result

    result["online"] = True
    info = parse_pong(data)
    if info:
        parts = info.split(";")
        name = parts[2].strip() if len(parts) > 2 else ""
        if len(parts) > 4 and parts[4].strip().isdigit():
            result["players"] = int(parts[4])
        match = PLAYERS_RE.search(name)
        if match:
            result["players"] = int(match.group(1))
            name = PLAYERS_RE.sub("", name).strip()
        result["name"] = name or None
    return result


def _read_previous(status_path):
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            prev = json.load(f)
    except (OSError, ValueError):
        return {}
    servers = prev.get("servers", []) if isinstance(prev, dict) else prev
    return {s.get("address"): s for s in servers if isinstance(s, dict)}


def _write_atomic(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    os.replace(tmp, path)


def run_ping(servers=None, status_path=None, interval=None):
    """Ping every server in parallel, then write status.json and append to history."""
    servers = servers if servers is not None else config.load_servers()
    status_path = status_path or config.STATUS_PATH
    interval = interval or config.PING_INTERVAL
    now_ms = int(time.time() * 1000)
    prev = _read_previous(status_path)

    with ThreadPoolExecutor(max_workers=min(16, max(1, len(servers)))) as pool:
        live = list(pool.map(lambda s: get_server_status(s["address"]), servers))

    results = []
    for entry, status in zip(servers, live):
        addr = entry["address"]
        before = prev.get(addr, {})
        res = {
            "address": addr,
            "online": status["online"],
            "players": status["players"],
            "version": entry.get("version") or "Unknown",
            "show_link": bool(entry.get("show_link", False)),
            "website": entry.get("website"),
        }

        # Name: a locked name always wins, then the live MOTD, then the last known name, then config.
        if entry.get("lock_name") and entry.get("name"):
            res["name"] = entry["name"]
        else:
            res["name"] = status["name"] or before.get("name") or entry.get("name") or addr

        if status["online"]:
            last_seen = before.get("last_seen")
            gap_ms = now_ms - int(last_seen) if last_seen else None
            # Keep counting only if it was online last check and the checker wasn't stopped in between.
            if before.get("online") and gap_ms is not None and gap_ms <= interval * 1000 * 4:
                res["uptime_seconds"] = float(before.get("uptime_seconds") or 0) + gap_ms / 1000
            else:
                res["uptime_seconds"] = 0.0
            res["last_seen"] = now_ms
        else:
            res["uptime_seconds"] = 0.0
            res["last_seen"] = before.get("last_seen")

        results.append(res)

    try:
        db.log_history(results, now_ms)
        db.prune_before(now_ms - config.HISTORY_DAYS * 86400 * 1000)
    except Exception as exc:  # history is nice-to-have; never stop the status file being written
        print(f"[ping] could not write history: {exc}")

    _write_atomic(status_path, {"checked_at": now_ms, "interval": interval, "servers": results})
    return results


def run_loop(interval=None, status_path=None, stop_event=None):
    """Ping forever, every `interval` seconds, until Ctrl+C or `stop_event` is set."""
    interval = interval or config.PING_INTERVAL
    db.init_db()
    while True:
        started = time.monotonic()
        try:
            run_ping(status_path=status_path, interval=interval)
        except Exception as exc:
            print(f"[ping] check failed: {exc}")
        wait = max(1.0, interval - (time.monotonic() - started))
        if stop_event is not None:
            if stop_event.wait(wait):
                return
        else:
            time.sleep(wait)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCPI server status checker")
    parser.add_argument("--loop", action="store_true", help="keep checking on an interval")
    parser.add_argument("--interval", type=float, default=config.PING_INTERVAL,
                        help=f"seconds between checks (default {config.PING_INTERVAL:g})")
    parser.add_argument("--status-path", default=config.STATUS_PATH, help="where to write status JSON")
    args = parser.parse_args()

    if args.loop:
        try:
            run_loop(interval=args.interval, status_path=args.status_path)
        except KeyboardInterrupt:
            pass
    else:
        db.init_db()
        for s in run_ping(status_path=args.status_path, interval=args.interval):
            print(f"{'UP  ' if s['online'] else 'DOWN'}  {s['address']:<35} {s['name']}")
