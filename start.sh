#!/bin/bash

# Navigate to the project root (where this script lives)
cd "$(dirname "$0")"

# Kill any existing server on port 5002
lsof -ti :5002 | xargs kill -9 2>/dev/null
sleep 1

# Activate the virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment 'venv' not found. Run: python3 -m venv venv && pip install -r backend/requirements.txt"
    exit 1
fi

# Set environment variables
export FLASK_ENV=development

# Start the Flask backend server
echo "🚀 Starting FRC Scouting App on http://127.0.0.1:5002 ..."
python3 backend/app.py
