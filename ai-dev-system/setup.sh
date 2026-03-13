#!/usr/bin/env bash
# ============================================================
#  AI Dev System — Setup script (Linux / macOS)
#  Run from the project root: bash setup.sh
# ============================================================
set -e

echo "[1/5] Creating virtual environment..."
python3 -m venv .venv

echo "[2/5] Activating virtual environment..."
source .venv/bin/activate

echo "[3/5] Installing dependencies..."
pip install -r requirements.txt

echo "[4/5] Copying env file (skip if .env already exists)..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "      .env created — remember to fill in your API keys!"
else
    echo "      .env already exists, skipping."
fi

echo "[5/5] Verifying import chain..."
python -c "from src.api.app import create_app; print('  Import OK')"

echo ""
echo "============================================================"
echo " Setup complete. Start the server with:"
echo "   source .venv/bin/activate"
echo "   python main.py"
echo "============================================================"
