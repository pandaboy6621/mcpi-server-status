@echo off
rem One-command start for Windows: sets up a virtualenv on first run, then starts the app.
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo Setting up virtual environment in .venv ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo Python 3 is required. Install it from https://www.python.org/downloads/
        exit /b 1
    )
)

.venv\Scripts\python.exe -c "import flask, waitress" 2>nul
if errorlevel 1 (
    echo Installing dependencies ...
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
)

.venv\Scripts\python.exe app.py %*
