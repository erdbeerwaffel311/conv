#!/usr/bin/env bash
# macOS double-clickable launcher for Universal Media Converter
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

# Ensure Homebrew and standard paths are in PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Virtuelle Umgebung wird erstellt..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r 1_resources/requirements.txt
fi

echo "Starte Universal Media Converter..."
exec .venv/bin/python3 2_code/gui.py
