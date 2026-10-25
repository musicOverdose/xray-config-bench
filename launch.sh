#!/usr/bin/env bash
# ==============================================================================
# Xray Config Bench — Desktop Application Launcher
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Setup / activate virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "[Xray Config Bench] Initializing Python virtual environment in .venv..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r requirements.txt
fi

source "$VENV_DIR/bin/activate"

# Launch main application
echo "[Xray Config Bench] Launching application..."
exec python3 main.py "$@"
