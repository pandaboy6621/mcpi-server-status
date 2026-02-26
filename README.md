# mcpi-server-status
a basic webpage that monitors the status of mcpi edition minecraft servers

## Setup (macOS / Linux)

1. Clone the repo

```bash
git clone https://github.com/pandaboy6621/mcpi-server-status.git
```

2. Create venv enviroment for dependencies
```bash
python -m venv venv
```

3. Activate the bundled Python virtual environment in the project root:

```bash
source venv/bin/activate
```

4. Install dependencies into environment:

```bash
pip install flask
```

```bash
pip install cryptography
```

5. Running the background status checker

The ping/checker must run continuously and independently from the web server. Use the `ping.py` script in loop mode to write `status.json` and log history to the database:

```bash
python ping.py --loop --interval 15
```

Recommended options:
- `--loop` : run continuously
- `--interval` : seconds between pings (default 15)
- `--status-path` : alternative path for the JSON output (default `status.json`)

You can run the checker as a background process (`nohup`, `screen`, `tmux`) or configure a system service (systemd/launchd) so it always runs. The web app will only read the `status.json` file and will not perform pings itself.

6. Start the web app:

```bash
python app.py
```
