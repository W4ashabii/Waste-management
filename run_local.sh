#!/bin/bash

# Local Development Script - Run services without Docker networking
# This bypasses Docker networking issues by running services locally
# Uses SQLite by default for simpler setup

echo "=== Starting Waste Management MVP (Local Mode) ==="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

# Use SQLite for simplicity
export DATABASE_URL="sqlite+aiosqlite:///./waste_management.db"
echo "Using SQLite database: waste_management.db"

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0
    else
        return 1
    fi
}

# Check if ports are available
if check_port 8001; then
    echo "Port 8001 is already in use. Please stop the service using it."
    exit 1
fi

if check_port 8000; then
    echo "Port 8000 is already in use. Please stop the service using it."
    exit 1
fi

# Start Model Service
echo "Starting Model Service on port 8001..."
cd model-service
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt || echo "Some packages may have failed, continuing..."
export MOCK_MODE="true"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
MODEL_PID=$!
cd ..

# Wait for model service to start
sleep 3

# Start Backend
echo "Starting Backend on port 8000..."
cd backend
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt || echo "Some packages may have failed, continuing..."
export MODEL_SERVICE_URL="http://localhost:8001"
export SECRET_KEY="dev-secret-key-change-in-production"
export ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES="30"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Seed database
echo "Seeding database..."
cd backend
source venv/bin/activate 2>/dev/null || source venv/bin/activate
python3 seed_db.py
cd ..

echo ""
echo "=== Services Started Successfully ==="
echo ""
echo "Services running at:"
echo "  - Backend API: http://localhost:8000"
echo "  - Model Service: http://localhost:8001"
echo "  - Frontend files: ./frontend/"
echo ""
echo "To view frontends, open the HTML files directly in your browser:"
echo "  - User: file://$(pwd)/frontend/user/index.html"
echo "  - Ward: file://$(pwd)/frontend/ward/index.html"
echo "  - Municipality: file://$(pwd)/frontend/municipality/index.html"
echo ""
echo "Test Credentials:"
echo "  - User: user@example.com / user123"
echo "  - Ward Admin: ward@example.com / ward123"
echo "  - Municipality Admin: municipality@example.com / muni123"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $MODEL_PID $BACKEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script running
wait
