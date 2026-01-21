import socket
import struct
import time
import random
import json
import os
import db
import re

# Default server list used when none provided to run_ping
SERVERS = [
    {"address": "thebrokenrail.com", "name": "Official MCPI Server!", "version": "TBR Cerberus 3.0.0", "show_link": True},
    {"address": "mcpi.izor.in", "name": None, "version": "2.5.3", "show_link": True},
    {"address": "pbpt.dog", "name": None, "version": "Unknown", "show_link": False},
    {"address": "beiop.net:19134", "name": "2.5.4", "version": "2.5.4", "show_link": False},
    {"address": "beiop.net:19135", "name": "2.5.4", "version": "2.5.4", "show_link": False},
    {"address": "beiop.net:19136", "name": "2.5.4", "version": "2.5.4", "show_link": False},
]

# GLOBAL COOLDOWN TRACKING
# Prevents database duplication and excessive network traffic
LAST_RUN_TIME = 0

def get_server_status(address_str):
    timeout = 5
    result = {
        "name": address_str,
        "online": False,
        "version": None,
        "uptime_seconds": 0,
        "address": address_str,
        "players": None,
    }

    sock = None
    try:
        if ":" in address_str:
            host, port = address_str.split(":", 1)
            target = (host, int(port))
        else:
            target = (address_str, 19132)

        magic = b"\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x124Vx"
        packet = b"\x02" + struct.pack(">q", random.randint(5, 20)) + magic

        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(packet, target)

        data = sock.recvfrom(2048)[0]

        server_name = None
        proto_or_version = None
        player_count = None
        try:
            if len(data) > 34:
                len_val = data[34]
                info_bytes = data[35:35 + len_val]
                info_str = info_bytes.decode("utf-8", errors="ignore")
                parts = info_str.split(";")
                if len(parts) > 2:
                    server_name = parts[2]
                if len(parts) > 1:
                    proto_or_version = parts[1]
                if len(parts) > 4:
                    player_count = parts[4]
        except Exception:
            server_name = None
            proto_or_version = None
            player_count = None

        result["online"] = True
        result["version"] = proto_or_version if proto_or_version else result.get("version")
        result["name"] = server_name if server_name else address_str
        result["players"] = player_count

        # Special handling for mcpi.izor.in
        if result["address"] == "mcpi.izor.in" or (result["name"] and "mcpi.izor.in" in result["name"]):
            match = re.search(r"(\d+)\s+connected players", result["name"] or "")
            if match:
                result["players"] = match.group(1)
            result["name"] = "mcpi.izor.in"

    except Exception:
        pass
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass

    return result


def run_ping(servers=None, status_path="status.json"):
    """
    Runs status checks and writes results to JSON and SQLite.
    Includes a 30-second cooldown to prevent file/DB duplication.
    """
    global LAST_RUN_TIME
    now_ms = int(time.time() * 1000)
    
    # Check cooldown: only run if it's been more than 30 seconds since the last run
    if now_ms - LAST_RUN_TIME < 30000:
        return 

    LAST_RUN_TIME = now_ms
    if servers is None:
        servers = SERVERS

    prev = {}
    if os.path.exists(status_path):
        try:
            with open(status_path, "r") as f:
                prev_list = json.load(f)
            for e in prev_list:
                prev[e.get("address") or e.get("name")] = e
        except Exception:
            prev = {}

    all_data = []

    for entry in servers:
        if isinstance(entry, dict):
            addr = entry.get("address")
            static_version = entry.get("version")
            static_name = entry.get("name")
            show_link = entry.get("show_link", False)
        else:
            addr = entry
            static_version = None
            static_name = None
            show_link = False

        res = get_server_status(addr)
        res["address"] = addr
        res["show_link"] = show_link

        key = addr
        prev_entry = prev.get(key, {})

        # Persist name if offline or if current ping didn't return a name
        if res.get("name") == addr:
            if prev_entry.get("name") and prev_entry.get("name") != addr:
                res["name"] = prev_entry["name"]
            elif static_name:
                res["name"] = static_name

        if res.get("online"):
            if prev_entry.get("online") and prev_entry.get("last_seen"):
                delta = (now_ms - int(prev_entry.get("last_seen"))) / 1000.0
                res["uptime_seconds"] = float(prev_entry.get("uptime_seconds", 0)) + delta
            else:
                res["uptime_seconds"] = float(prev_entry.get("uptime_seconds", 0))
            res["last_seen"] = now_ms
        else:
            res["last_seen"] = prev_entry.get("last_seen")
            res["uptime_seconds"] = float(prev_entry.get("uptime_seconds", 0))

        if static_version is not None:
            res["version"] = static_version

        # Final cleanup for specific servers
        if res.get("address") == "mcpi.izor.in":
            res["name"] = "mcpi.izor.in"

        all_data.append(res)

    # Log to real SQLite database via db.py
    try:
        # use db module default path (absolute inside project) to avoid multiple DB files
        db.log_history(all_data, now_ms)
    except Exception:
        pass

    # Update status.json atomicly
    try:
        tmp_path = status_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(all_data, f, indent=4)
        os.replace(tmp_path, status_path)
    except Exception:
        try:
            with open(status_path, "w") as f:
                json.dump(all_data, f, indent=4)
        except:
            pass

if __name__ == "__main__":
    run_ping()