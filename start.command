#!/bin/bash
# ============================================================
#  🎬 YouTube Automation - One Click Launcher
#  Double-click this file to start the web terminal
# ============================================================

# Change to the script's directory
cd "$(dirname "$0")"

echo "════════════════════════════════════════════════════════════════════"
echo "   🎬 YouTube Automation Web Terminal"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found, using system Python"
fi

# Check if required modules are installed
echo "🔍 Checking dependencies..."
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies. Installing..."
    pip install fastapi uvicorn websockets python-dotenv
fi

echo ""
echo "🚀 Starting server on http://localhost:8000"
echo "🌐 Opening browser in 2 seconds..."
echo ""
echo "   Press Ctrl+C to stop the server"
echo "────────────────────────────────────────────────────────────────────"
echo ""

# Open browser after 2 seconds
(sleep 2 && open http://localhost:8000) &

# Run the web terminal
python3 web_terminal.py
