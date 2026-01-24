# mcpi-server-status
a basic webpage that monitors the status of mcpi edition minecraft servers

## Running

- Create and activate a virtualenv, then install dependencies from `requirements.txt`.
- Start the web app with `python app.py`.

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
