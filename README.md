# mcpi-server-status
a basic webpage that monitors the status of mcpi edition minecraft servers

## Running

- Create and activate a virtualenv, then install dependencies from `requirements.txt`.
- Start the web app with `python app.py`.
 - Activate the repository virtualenv `.venv`, then (if needed) install dependencies from `requirements.txt`.
 - Start the web app with `python app.py`.

## Running the background status checker

The ping/checker must run continuously and independently from the web server. Use the `ping.py` script in loop mode to write `status.json` and log history to the database:

## Setup (macOS / Linux)

1. Activate the bundled Python virtual environment in the project root:

```bash
source .venv/bin/activate
```

2. (Optional) Install dependencies if they're not already present in the bundled environment:

```bash
pip install -r requirements.txt
```

3. Start the web app:

```bash
python app.py
```

## Running the background status checker

The ping/checker must run continuously and independently from the web server. Use the `ping.py` script in loop mode to write `status.json` and log history to the database:

```bash
# from your virtualenv in the project root
python ping.py --loop --interval 15
```

Recommended options:
- `--loop` : run continuously
- `--interval` : seconds between pings (default 15)
- `--status-path` : alternative path for the JSON output (default `status.json`)

You can run the checker as a background process (`nohup`, `screen`, `tmux`) or configure a system service (systemd/launchd) so it always runs. The web app will only read the `status.json` file and will not perform pings itself.

## Updating the deployed web server (repull or replace)

On the server you deployed to, you can either "repull" the existing repository (recommended) or fully replace it with a fresh clone.

Repull (update the existing directory, uses branch `main`):

```bash
# ssh into the server
ssh user@your-server

# (optional) stop the running web process or service. Adjust for how you run it:
# systemd example: sudo systemctl stop mcpi-server-status
# simple process: pkill -f "python app.py"

cd /path/to/mcpi-server-status
git fetch origin
git reset --hard origin/main

# reactivate the virtualenv and reinstall any new deps
source .venv/bin/activate
pip install -r requirements.txt

# restart the service/process
# systemd example: sudo systemctl start mcpi-server-status
```

Replace (remove old copy and clone fresh from your repo):

```bash
# ssh into the server
ssh user@your-server

# (optional) stop the running web process or service
# systemd example: sudo systemctl stop mcpi-server-status

cd /path/to
rm -rf mcpi-server-status
git clone --branch main <repo_url>
cd mcpi-server-status

# activate the repo-provided virtualenv and install deps if needed
source .venv/bin/activate
pip install -r requirements.txt

# start the service/process
# systemd example: sudo systemctl start mcpi-server-status
```

Replace `<repo_url>` with your repository HTTP/SSH URL. These commands assume the only branch you use is `main`.
