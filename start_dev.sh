#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo "Stopping processes..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID
    fi
    exit
}

trap cleanup SIGINT SIGTERM

# Kill existing processes on ports
echo "Checking for existing processes..."

# Kill process on port 8000 (Backend)
PORT_8000_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$PORT_8000_PID" ]; then
    echo "Killing process on port 8000 (PID: $PORT_8000_PID)..."
    kill -9 $PORT_8000_PID 2>/dev/null
    sleep 1
fi

# Kill process on port 5173 (Frontend - Vite default)
PORT_5173_PID=$(lsof -ti:5173 2>/dev/null)
if [ -n "$PORT_5173_PID" ]; then
    echo "Killing process on port 5173 (PID: $PORT_5173_PID)..."
    kill -9 $PORT_5173_PID 2>/dev/null
    sleep 1
fi

echo "Starting Backend..."
if [ -f ".venv/Scripts/python" ]; then
    PYTHON=".venv/Scripts/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi

$PYTHON backend/main.py &
BACKEND_PID=$!

echo "Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!

# Wait for processes
wait
