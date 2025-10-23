#!/bin/bash

# NQ Tenpin League System - Startup Script

echo "======================================"
echo "NQ Tenpin League Management System"
echo "Version 1.0"
echo "======================================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing required packages..."
pip install -q -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p static/img
mkdir -p static/css
mkdir -p static/js
mkdir -p backups
mkdir -p uploads

# Initialize database
echo "Initializing database..."
python3 -c "from app import init_db; init_db()"

echo ""
echo "======================================"
echo "Starting NQ Tenpin League System"
echo "======================================"
echo ""
echo "Application URL: http://localhost:2019"
echo ""
echo "Default Login Credentials:"
echo "Username: admin"
echo "Password: admin123"
echo ""
echo "IMPORTANT: Change the default password after first login!"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================"
echo ""

# Start the application
python3 app.py
