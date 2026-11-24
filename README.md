# mcpi-server-status

A small web page that shows whether **Minecraft: Pi Edition** (MCPI / MCPI-Reborn) servers are online, with player counts, current uptime and a 24-hour heartbeat for each server.

- Live status, refreshed every 15 seconds
- 24-hour heartbeat (15-minute slots) and uptime percentage per server
- One-click "copy address" button for joining a server
- Warns you when the data is out of date (for example, if the checker has stopped)
- Server list lives in [`servers.json`](servers.json), so you don't have to edit code

## Quick start

### Option 1: Docker (easiest)

```bash
docker compose up -d
```

Open <http://localhost:5555>. Status history is kept in the `mcpi-data` volume. After editing `servers.json`, run `docker compose restart`.

Compose uses the prebuilt image from GitHub Container Registry, which is built for `amd64` and `arm64` (so it runs on a Raspberry Pi). Run `docker compose up -d --build` to build it from your local source instead.

Without Compose:

```bash
docker run -d -p 5555:5555 -v mcpi-data:/data --restart unless-stopped \
  --name mcpi-server-status ghcr.io/pandaboy6621/mcpi-server-status:latest
```

To use your own server list, add `-v "$PWD/servers.json:/app/servers.json:ro"`.

Image tags: `latest` (newest `main`), `1.0.0`-style release versions, and `sha-<commit>`.

### Option 2: Run script (macOS / Linux / Windows)

You need Python 3.9 or newer.

```bash
git clone https://github.com/pandaboy6621/mcpi-server-status.git
cd mcpi-server-status
./run.sh
```

On Windows, double-click `run.bat` or run it from a terminal.

The first run creates a `.venv` and installs the dependencies. After that it starts straight away. Open <http://localhost:5555>.

### Option 3: Manual

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

`app.py` runs both the web page and the background checker, so you don't need to run `ping.py` separately.

## Adding or removing servers

Edit [`servers.json`](servers.json):

```json
{
    "address": "example.com:19132",
    "name": "Fallback name if the server doesn't send one",
    "version": "2.5.4",
    "show_link": true,
    "website": "https://example.com"
}
```

| Field       | Required | Meaning |
|-------------|----------|---------|
| `address`   | yes      | `host` or `host:port` (default port 19132) |
| `name`      | no       | Name to show until the server reports its own name |
| `lock_name` | no       | `true` always shows `name`, ignoring the name the server sends |
| `version`   | no       | Version label shown on the card |
| `website`   | no       | Link shown on the card |
| `show_link` | no       | `true` links to `http://<host>` when there's no `website` |

Restart the app after you change the list.

## Options

```text
python app.py [--port 5555] [--host 0.0.0.0] [--interval 30] [--no-checker] [--https]
```

| Flag / env var                              | Default  | What it does |
|---------------------------------------------|----------|--------------|
| `--port` / `MCPI_PORT`                      | `5555`   | Web port |
| `--host` / `MCPI_HOST`                      | `0.0.0.0`| Listen address (`127.0.0.1` = this computer only) |
| `--interval` / `MCPI_PING_INTERVAL`         | `30`     | Seconds between server checks |
| `--no-checker`                              |          | Only serve the page. Run `python ping.py --loop` somewhere else |
| `--https`                                   |          | Self-signed HTTPS (needs `pip install pyopenssl`) |
| `MCPI_DATA_DIR`                             | `./data` | Where `status.json` and `status.db` are stored |
| `MCPI_HISTORY_DAYS`                         | `7`      | How long to keep history before deleting it |
| `MCPI_SERVERS_FILE`                         | `./servers.json` | Path to the server list |

Check every server once from the terminal:

```bash
python ping.py
```

## How it works

- `ping.py` sends a RakNet "unconnected ping" over UDP to each server in parallel. It writes the results to `data/status.json` and appends them to a SQLite history in `data/status.db`.
- `app.py` is a Flask app (served with waitress) that runs the checker in a background thread and serves the page, `/status.json`, `/history.json` and `/healthz`.
- The page in `templates/` and `static/` loads both JSON files and redraws every 15 seconds.

> **Note:** the checker uses UDP. If every server shows offline, check that your firewall or network allows outbound UDP to port 19132.
