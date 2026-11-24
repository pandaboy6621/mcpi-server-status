#!/usr/bin/env bash
# One-command start for macOS / Linux: sets up a virtualenv on first run, then starts the app.
# Any arguments are passed to app.py, e.g. ./run.sh --port 8080
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-$(command -v python3 || command -v python || true)}"
if [ -z "$PYTHON" ]; then
    echo "Python 3 is required. Install it from https://www.python.org/downloads/" >&2
    exit 1
fi

if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c 'import sys' 2>/dev/null; then
    echo "Setting up virtual environment in .venv ..."
    rm -rf .venv
    "$PYTHON" -m venv .venv
fi

if ! .venv/bin/python -c 'import flask, waitress' 2>/dev/null || [ requirements.txt -nt .venv/.installed ]; then
    echo "Installing dependencies ..."
    .venv/bin/python -m pip install --quiet --upgrade pip
    .venv/bin/python -m pip install --quiet -r requirements.txt
    touch .venv/.installed
fi

exec .venv/bin/python app.py "$@"
