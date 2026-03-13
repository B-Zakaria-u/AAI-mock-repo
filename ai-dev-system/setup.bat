@echo off
REM ============================================================
REM  AI Dev System — Setup script (run from project root)
REM ============================================================

echo [1/5] Creating virtual environment...
python -m venv .venv

echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [3/5] Installing dependencies...
pip install -r requirements.txt

echo [4/5] Copying env file (skip if .env already exists)...
if not exist .env (
    copy .env.example .env
    echo      .env created — remember to fill in your API keys!
) else (
    echo      .env already exists, skipping.
)

echo [5/5] Verifying import chain...
python -c "from src.api.app import create_app; print('  Import OK')"

echo.
echo ============================================================
echo  Setup complete. Start the server with:
echo    .venv\Scripts\activate
echo    python main.py
echo ============================================================
pause
