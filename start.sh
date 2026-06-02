#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  The Scriptorium — LAN Launch Script (macOS / Linux)
#  Starts the server on all network interfaces so collaborators can connect.
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

if [ ! -f "venv/bin/streamlit" ]; then
    echo ""
    echo "  [ERROR] Virtual environment not found."
    echo "  Run the following to set it up:"
    echo ""
    echo "    python3 -m venv venv"
    echo "    venv/bin/pip install -r requirements.txt"
    echo ""
    exit 1
fi

echo ""
echo "  ================================================"
echo "   THE SCRIPTORIUM  |  Prose Generation Studio"
echo "  ================================================"
echo ""
echo "  Server starting on all network interfaces (port 8501)."
echo ""
echo "  Local:    http://localhost:8501"
echo ""

# Print local IP addresses
if command -v ip &>/dev/null; then
    LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
elif command -v ifconfig &>/dev/null; then
    LAN_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
fi

if [ -n "$LAN_IP" ]; then
    echo "  LAN:      http://${LAN_IP}:8501"
fi

echo ""
echo "  Press Ctrl+C to stop."
echo ""

venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
