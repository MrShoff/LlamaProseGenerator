@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  The Scriptorium — LAN Launch Script (Windows)
REM  Starts the server on all network interfaces so collaborators can connect.
REM ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0"

if not exist "venv\Scripts\streamlit.exe" (
    echo.
    echo  [ERROR] Virtual environment not found.
    echo  Run the following to set it up:
    echo.
    echo    python -m venv venv
    echo    venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo  ================================================
echo   THE SCRIPTORIUM  ^|  Prose Generation Studio
echo  ================================================
echo.
echo  Server starting on all network interfaces ^(port 8501^).
echo.
echo  Local:    http://localhost:8501
echo.
echo  LAN:      Find your IP with:  ipconfig
echo            Then share:  http://YOUR_IP:8501
echo.
echo  Press Ctrl+C to stop.
echo.

venv\Scripts\streamlit.exe run app.py --server.address 0.0.0.0 --server.port 8501
