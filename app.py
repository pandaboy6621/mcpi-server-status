"""MCPI Server Status web app.

    python app.py              # web page + background checker on http://localhost:5555
    python app.py --help       # all options
"""
import argparse
import json
import os
import threading
import time

from flask import Flask, jsonify, render_template

import config
import db
import ping

HEARTBEAT_BUCKETS = 96          # 24h split into 15-minute slots
BUCKET_MS = 15 * 60 * 1000

app = Flask(__name__)


def _read_status():
    try:
        with open(config.STATUS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"servers": [], "checked_at": 0, "interval": config.PING_INTERVAL}
    if isinstance(data, list):  # old format: a bare list, timestamp = file mtime
        data = {"servers": data, "checked_at": int(os.path.getmtime(config.STATUS_PATH) * 1000)}
    data.setdefault("interval", config.PING_INTERVAL)
    return data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status.json")
def status_json():
    data = _read_status()
    # Online first, then keep the order from servers.json.
    data["servers"] = sorted(data.get("servers", []), key=lambda s: not s.get("online"))
    data["server_time"] = int(time.time() * 1000)
    return jsonify(data)


@app.route("/history.json")
def history_json():
    """Per server: 96 slots covering the last 24h. 1 = seen online, 0 = only seen offline, null = no data."""
    now_ms = int(time.time() * 1000)
    since_ms = now_ms - HEARTBEAT_BUCKETS * BUCKET_MS
    addresses = [s["address"] for s in config.load_servers()]
    history = {a: [None] * HEARTBEAT_BUCKETS for a in addresses}

    for row in db.fetch_history_since(since_ms):
        buckets = history.get(row["address"])
        if buckets is None:
            continue
        idx = (row["recorded_at"] - since_ms) // BUCKET_MS
        if 0 <= idx < HEARTBEAT_BUCKETS:
            buckets[idx] = 1 if row["online"] or buckets[idx] == 1 else 0

    return jsonify({
        "since": since_ms,
        "bucket_ms": BUCKET_MS,
        "servers": [{"address": a, "buckets": b} for a, b in history.items()],
    })


@app.route("/healthz")
def healthz():
    checked_at = _read_status().get("checked_at") or 0
    fresh = (time.time() * 1000 - checked_at) < config.PING_INTERVAL * 1000 * 4
    return jsonify({"ok": fresh, "checked_at": checked_at}), (200 if fresh else 503)


def start_checker(interval):
    stop = threading.Event()
    thread = threading.Thread(
        target=ping.run_loop, kwargs={"interval": interval, "stop_event": stop},
        name="mcpi-checker", daemon=True,
    )
    thread.start()
    return stop


def main():
    parser = argparse.ArgumentParser(description="MCPI Server Status")
    parser.add_argument("--host", default=os.environ.get("MCPI_HOST", "0.0.0.0"),
                        help="address to listen on (default 0.0.0.0 = whole network)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCPI_PORT", "5555")))
    parser.add_argument("--interval", type=float, default=config.PING_INTERVAL,
                        help=f"seconds between server checks (default {config.PING_INTERVAL:g})")
    parser.add_argument("--no-checker", action="store_true",
                        help="only serve the page; run `python ping.py --loop` separately")
    parser.add_argument("--https", action="store_true",
                        help="serve over HTTPS with a self-signed cert (needs `pip install pyopenssl`)")
    args = parser.parse_args()

    db.init_db()
    config.PING_INTERVAL = args.interval
    if not args.no_checker:
        start_checker(args.interval)

    scheme = "https" if args.https else "http"
    shown_host = "localhost" if args.host in ("0.0.0.0", "::") else args.host
    print(f"\n  MCPI Server Status running at {scheme}://{shown_host}:{args.port}\n"
          f"  Checking {len(config.load_servers())} servers every {args.interval:g}s. Press Ctrl+C to stop.\n", flush=True)
    if args.https:
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False, ssl_context="adhoc")
        return
    try:
        from waitress import serve
    except ImportError:  # fall back to Flask's built-in server
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    else:
        serve(app, host=args.host, port=args.port, threads=8)


if __name__ == "__main__":
    main()
