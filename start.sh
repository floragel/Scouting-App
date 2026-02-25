#!/bin/bash

# Navigate to the script's directory so it works from anywhere
cd "$(dirname "$0")"

# Activate the virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment 'venv' not found. Please ensure it's set up."
fi

# Set FLASK_APP or any other environment variables if needed
export FLASK_ENV=development

# Start the Flask backend server
echo "Starting FRC Scouting App Backend..."
python3 backend/app.py
