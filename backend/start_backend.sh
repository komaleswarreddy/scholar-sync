#!/bin/bash

# Backend Startup Script
# This will start the backend in the current terminal so you can see all logs

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting ScholarSync Backend"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Backend will run on: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/api/docs"
echo ""
echo "📺 All logs will appear in this terminal"
echo "   - 🔍 Debug messages"
echo "   - 📊 Processing steps"  
echo "   - ✅ Success messages"
echo "   - ❌ Errors"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Activated venv"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Activated .venv"
else
    echo "⚠️  No virtual environment found. Using system Python."
fi

# Start the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

