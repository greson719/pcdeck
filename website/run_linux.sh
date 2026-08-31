#!/usr/bin/env bash
# ==============================================================================
# PCDeck Pro - Universal Linux Launcher
# ==============================================================================
set -e

echo "🐧 Starting PCDeck Pro on Linux..."

# Check for Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install python3 (e.g., sudo apt install python3 python3-pip python3-tk)"
    exit 1
fi

# If uv is available, use uv for sub-second startup
if command -v uv &>/dev/null; then
    echo "⚡ Using uv package manager..."
    uv run python3 server/main.py "$@"
else
    # Fallback to python3 / venv
    if [ ! -d ".venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r pyproject.toml || pip install fastapi uvicorn "websockets>=12.0" "qrcode[pil]" pillow mss pynput psutil
    else
        source .venv/bin/activate
    fi
    python3 server/main.py "$@"
fi
